
"""
金十实时市场监控
============================================================

完整流程：

    金十 WebSocket
        ↓
    新闻清洗
        ↓
    市场分类
        ↓
    A股 / 美股 Claude 情绪分析
        ↓
    JSONL 留底
        ↓
    backend.py
        ↓
    static/index.html Dashboard

本版本：
    1. 完全取消企业微信推送
    2. 有方向性的 A股 / 美股新闻直接写入 JSONL
    3. backend.py 读取 JSONL
    4. HTML Dashboard 每5秒请求 /api/live 自动刷新
    5. Claude API Key 不写在代码中
    6. 金十 Secret Key 不写在代码中


市场分类逻辑
------------------------------------------------------------

第一层：只认明确父分类

    29 = A股
    27 = 美股
    28 = 港股

    只有29           → A股
    只有27           → 美股
    只有28           → 港股

    29 + 28          → A股
    27 + 28          → 美股

    27 + 29
    27 + 28 + 29
        → 进入硬证据判断


第二层：硬证据

    A股：
        a_shares字段
        600519.SH / 300750.SZ / xxxxxx.BJ
        A股 / 沪指 / 上证指数 / 创业板指 等

    美股：
        NVDA.O / TME.N / XXX.A
        美股 / 纳指 / 标普500 / 道指 / NASDAQ / NYSE

    港股：
        00700.HK / 09988.HK
        港股 / 恒指 / 恒生科技指数 等


第三层：

    A股和美股都有非常强的硬证据
        → A股+美股
        → 两个prompt都跑

    仍无法确定
        → 未知/其他
        → 留底，不打分


后续：

    A股
        → sentiment_prompt.txt

    美股
        → sentiment_prompt(us).txt

    港股
        → 留底，不打分

    未知/其他
        → 留底，不打分


A股：

    关卡A中性新闻
        → jin10_gate_a_digest.jsonl


美股：

    关卡F分析师评级
        → jin10_us_analyst_digest.jsonl


有方向性的A股/美股：

    → jin10_live_scored.jsonl

    同时分别进入：

    A股
        → jin10_live_scored_a.jsonl

    美股
        → jin10_live_scored_us.jsonl


Dashboard：

    backend.py
        ↓
    读取：
        jin10_live_scored_a.jsonl
        jin10_live_scored_us.jsonl
        ↓
    /api/live
        ↓
    static/index.html
        ↓
    浏览器每5秒刷新一次


运行前：

    pip install websocket-client requests anthropic


环境变量：

    export JIN10_SECRET_KEY="你的金十secret-key"

    export ANTHROPIC_API_KEY="你的Anthropic API key"


注意：

    Anthropic() 默认自动读取：

        ANTHROPIC_API_KEY

    所以交接给其他人以后，
    对方只需要设置自己的 Claude API Key。

    不需要修改本 Python 文件。
"""


# ============================================================
# Imports
# ============================================================

import os
import json
import re
import time
import queue
import threading

from datetime import datetime
from pathlib import Path

import requests
import websocket

from anthropic import Anthropic


# ============================================================
# 1. 金十配置
# ============================================================

WS_URL = "wss://open-api-ws.jin10.com/flash"
CLASSIFY_API_URL = "https://open-data-api.jin10.com/data-api/flash/classify"
SECRET_KEY = os.getenv("JIN10_SECRET_KEY", "").strip()

APP_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = APP_DIR.parent
PROMPT_DIR = PACKAGE_DIR / "prompts"
DATA_DIR = Path(os.getenv("DAILY_SUMMARY_DATA_DIR", PACKAGE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_RAW_MESSAGES = os.getenv("DAILY_SUMMARY_LOG_RAW_MESSAGES", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MAX_LOG_BYTES = int(os.getenv("DAILY_SUMMARY_MAX_LOG_BYTES", str(5 * 1024 * 1024)))

# ============================================================
# 2. Claude配置
# ============================================================

PROMPT_FILE = PROMPT_DIR / "sentiment_prompt.txt"

PROMPT_FILE_US = PROMPT_DIR / "sentiment_prompt_us.txt"


CLAUDE_MODEL = os.getenv("DAILY_SUMMARY_CLAUDE_MODEL", "claude-sonnet-4-6")


CLAUDE_MAX_RETRIES = 3

CLAUDE_RETRY_BACKOFF = 5


# ------------------------------------------------------------
# 检查 Claude API Key
#
# 不把Key写进代码。
#
# Anthropic() 会自动读取：
#
# ANTHROPIC_API_KEY
# ------------------------------------------------------------

claude_client = Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None


# ------------------------------------------------------------
# A股 Prompt
# ------------------------------------------------------------

with open(
    PROMPT_FILE,
    encoding="utf-8"
) as f:

    SYSTEM_PROMPT_A = (
        f.read()
    )


# ------------------------------------------------------------
# 美股 Prompt
# ------------------------------------------------------------

with open(
    PROMPT_FILE_US,
    encoding="utf-8"
) as f:

    SYSTEM_PROMPT_US = (
        f.read()
    )


# ============================================================
# 3. 文件配置
# ============================================================

LOG_FILE = DATA_DIR / "jin10_stock_live_log.txt"


RAW_LOG_FILE = DATA_DIR / "jin10_stock_raw_messages.jsonl"


CLEAN_LOG_FILE = DATA_DIR / "jin10_stock_clean_messages.jsonl"


# ------------------------------------------------------------
# 市场分类后的全量数据
# ------------------------------------------------------------

CLASSIFIED_A_FILE = DATA_DIR / "jin10_classified_a.jsonl"


CLASSIFIED_US_FILE = DATA_DIR / "jin10_classified_us.jsonl"


CLASSIFIED_HK_FILE = DATA_DIR / "jin10_classified_hk.jsonl"


CLASSIFIED_A_US_FILE = DATA_DIR / "jin10_classified_a_us.jsonl"


CLASSIFIED_UNKNOWN_FILE = DATA_DIR / "jin10_classified_unknown.jsonl"


# ------------------------------------------------------------
# Claude打分结果
# ------------------------------------------------------------

SCORED_LOG_FILE = DATA_DIR / "jin10_live_scored.jsonl"


SCORED_LOG_A_FILE = DATA_DIR / "jin10_live_scored_a.jsonl"


SCORED_LOG_US_FILE = DATA_DIR / "jin10_live_scored_us.jsonl"


# ------------------------------------------------------------
# 日报来源
# ------------------------------------------------------------

GATE_A_DIGEST_FILE = DATA_DIR / "jin10_gate_a_digest.jsonl"


US_ANALYST_DIGEST_FILE = DATA_DIR / "jin10_us_analyst_digest.jsonl"


# ------------------------------------------------------------
# 状态文件
# ------------------------------------------------------------

PROCESSED_IDS_FILE = DATA_DIR / "jin10_stock_processed_ids.json"


CLASSIFY_MAP_FILE = DATA_DIR / "jin10_classify_map.json"


# ============================================================
# 4. WebSocket订阅
# ============================================================

SUBSCRIBE_PARAMS = {

    "category": [
        "3",
        "4"
    ]

}


RECONNECT_WAIT_SEC = 10


# ============================================================
# 5. 全局状态
# ============================================================

CLASSIFY_ID_TO_NAME = {}


# ------------------------------------------------------------
# 同一个ID的正文内容
# ------------------------------------------------------------

SEEN_NEWS_CONTENT = {}


# ------------------------------------------------------------
# 已完整处理的新闻
# ------------------------------------------------------------

PROCESSED_IDS = set()


processed_ids_lock = (
    threading.Lock()
)


# ------------------------------------------------------------
# Claude处理队列
# ------------------------------------------------------------

news_queue = (
    queue.Queue()
)


# ============================================================
# 6. 基础工具
# ============================================================

def log(msg):

    line = (
        f"["
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"] "
        f"{msg}"
    )

    print(
        line
    )

    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_BYTES:
            rotated = LOG_FILE.with_name(f"{LOG_FILE.name}.1")
            if rotated.exists():
                rotated.unlink()
            LOG_FILE.replace(rotated)
    except Exception:
        pass

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            line
            +
            "\n"
        )


def append_jsonl(
    path,
    record
):

    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(
        path,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(

            json.dumps(
                record,
                ensure_ascii=False
            )

            +

            "\n"
        )


# ============================================================
# 7. processed ids
# ============================================================

def load_processed_ids():

    try:

        with open(
            PROCESSED_IDS_FILE,
            encoding="utf-8"
        ) as f:

            data = json.load(
                f
            )

        return {

            str(x)

            for x in data

        }


    except FileNotFoundError:

        return set()


    except Exception as e:

        log(
            f"[警告] "
            f"processed ids读取失败: "
            f"{e}"
        )

        return set()


def mark_processed(
    news_id
):

    news_id = str(
        news_id
    )


    with processed_ids_lock:

        PROCESSED_IDS.add(
            news_id
        )


        with open(
            PROCESSED_IDS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(

                sorted(
                    PROCESSED_IDS
                ),

                f,

                ensure_ascii=False,

                indent=2
            )


# ============================================================
# 8. 重启时恢复内容去重记忆
# ============================================================

def rebuild_seen_content_from_log():

    try:

        with open(
            CLEAN_LOG_FILE,
            encoding="utf-8"
        ) as f:


            for line in f:

                try:

                    r = json.loads(
                        line
                    )


                    news_id = str(

                        r.get(
                            "id",
                            ""
                        )

                    )


                    content = str(

                        r.get(
                            "content",
                            ""
                        )

                        or ""

                    )


                    if news_id:

                        SEEN_NEWS_CONTENT[
                            news_id
                        ] = content


                except Exception:

                    continue


    except FileNotFoundError:

        pass


# ============================================================
# 9. classify map
# ============================================================

def fetch_classify_map(
    max_retries=4,
    retry_backoff=5
):

    headers = {

        "secret-key":
            SECRET_KEY

    }


    last_error = None


    for attempt in range(
        1,
        max_retries + 1
    ):


        try:

            resp = requests.get(

                CLASSIFY_API_URL,

                headers=headers,

                timeout=10

            )


            resp.raise_for_status()


            resp.encoding = (
                "utf-8"
            )


            result = (
                resp.json()
            )


            id_to_name = {}


            def walk(items):

                for item in items:

                    cid = item.get(
                        "id"
                    )


                    name = item.get(
                        "name"
                    )


                    if cid is not None:

                        id_to_name[
                            cid
                        ] = name


                    children = (

                        item.get(
                            "child"
                        )

                        or []

                    )


                    if children:

                        walk(
                            children
                        )


            walk(

                result.get(
                    "data",
                    []
                )

            )


            # =================================================
            # 保存本地缓存
            # =================================================

            try:

                with open(
                    CLASSIFY_MAP_FILE,
                    "w",
                    encoding="utf-8"
                ) as f:


                    json.dump(

                        {

                            str(k): v

                            for k, v
                            in id_to_name.items()

                        },

                        f,

                        ensure_ascii=False,

                        indent=2

                    )


            except Exception:

                pass


            return id_to_name


        except Exception as e:

            last_error = e


            if attempt < max_retries:

                wait = (

                    retry_backoff

                    *

                    (
                        2
                        **
                        (attempt - 1)
                    )

                )


                log(
                    f"[classify警告] "
                    f"第{attempt}次失败: "
                    f"{e}，"
                    f"{wait}秒后重试"
                )


                time.sleep(
                    wait
                )


    raise RuntimeError(

        f"classify映射表拉取失败: "
        f"{last_error}"

    )


def load_cached_classify_map():

    try:

        with open(
            CLASSIFY_MAP_FILE,
            encoding="utf-8"
        ) as f:

            cached = json.load(
                f
            )


        return {

            int(k): v

            for k, v
            in cached.items()

        }


    except Exception:

        return {}


def resolve_classify_names(
    classify_ids
):

    return [

        CLASSIFY_ID_TO_NAME.get(
            cid,
            f"未知ID:{cid}"
        )

        for cid
        in classify_ids

    ]


# ============================================================
# 10. A股股票代码判断
# ============================================================

def is_not_individual_stock(
    symbol
):

    if not symbol:

        return True


    valid_sz_prefixes = (

        "000",
        "001",
        "002",
        "003",
        "300",
        "301",
        "200",

    )


    valid_sh_prefixes = (

        "600",
        "601",
        "603",
        "605",
        "688",
        "689",

    )


    valid_bj_prefixes = (

        "4",
        "8",
        "9",

    )


    if symbol.endswith(
        ".SZ"
    ):

        return not symbol.startswith(
            valid_sz_prefixes
        )


    if symbol.endswith(
        ".SH"
    ):

        return not symbol.startswith(
            valid_sh_prefixes
        )


    if symbol.endswith(
        ".BJ"
    ):

        return not symbol.startswith(
            valid_bj_prefixes
        )


    return True


# ============================================================
# 11. 市场分类关键词
# ============================================================

A_KEYWORDS = (

    "A股",

    "沪指",

    "上证指数",

    "深证成指",

    "创业板指",

    "科创50",

    "北证50",

    "沪深300",

    "中证500",

    "中证1000",

    "沪深两市",

    "沪深股市",

    "沪深市场",

    "北交所",

)


US_KEYWORDS = (

    "美股",

    "纳斯达克",

    "纳指",

    "纳斯达克综合指数",

    "标普500",

    "标普 500",

    "标普500指数",

    "道琼斯",

    "道指",

    "纽约证券交易所",

    "纽交所",

    "NASDAQ",

    "NYSE",

)


HK_KEYWORDS = (

    "港股",

    "恒指",

    "恒生指数",

    "恒生科技指数",

    "恒生国企指数",

    "恒生中国企业指数",

    "港交所",

)


# ============================================================
# 12. 严格市场分类
# ============================================================

def classify_stock_market(
    record
):

    classify_ids = set(

        record.get(
            "classify_ids",
            []
        )

        or []

    )


    content = str(

        record.get(
            "content",
            ""
        )

        or ""

    )


    a_share_stocks = (

        record.get(
            "a_share_stocks",
            []
        )

        or []

    )


    # ========================================================
    # 父分类
    # ========================================================

    has_a = (
        29 in classify_ids
    )


    has_us = (
        27 in classify_ids
    )


    has_hk = (
        28 in classify_ids
    )


    # ========================================================
    # 单市场
    # ========================================================

    if (
        has_a
        and not has_us
        and not has_hk
    ):

        return (

            "A股",

            "single_parent",

            {
                "parent":
                    ["A股"]
            }

        )


    if (
        has_us
        and not has_a
        and not has_hk
    ):

        return (

            "美股",

            "single_parent",

            {
                "parent":
                    ["美股"]
            }

        )


    if (
        has_hk
        and not has_a
        and not has_us
    ):

        return (

            "港股",

            "single_parent",

            {
                "parent":
                    ["港股"]
            }

        )


    # ========================================================
    # A股 + 港股
    # ========================================================

    if (
        has_a
        and has_hk
        and not has_us
    ):

        return (

            "A股",

            "a_hk_priority",

            {
                "parent":
                    [
                        "A股",
                        "港股"
                    ]
            }

        )


    # ========================================================
    # 美股 + 港股
    # ========================================================

    if (
        has_us
        and has_hk
        and not has_a
    ):

        return (

            "美股",

            "us_hk_priority",

            {
                "parent":
                    [
                        "美股",
                        "港股"
                    ]
            }

        )


    # ========================================================
    # 硬证据评分
    # ========================================================

    a_score = 0

    us_score = 0

    hk_score = 0


    a_reasons = []

    us_reasons = []

    hk_reasons = []


    # --------------------------------------------------------
    # 父分类弱证据
    # --------------------------------------------------------

    if has_a:

        a_score += 1

        a_reasons.append(
            "父分类29"
        )


    if has_us:

        us_score += 1

        us_reasons.append(
            "父分类27"
        )


    if has_hk:

        hk_score += 1

        hk_reasons.append(
            "父分类28"
        )


    # ========================================================
    # A股硬证据
    # ========================================================

    if a_share_stocks:

        a_score += 5

        a_reasons.append(
            "a_share_stocks"
        )


    if re.search(

        r'(?<!\d)'
        r'\d{6}'
        r'\.(?:SH|SZ|BJ)'
        r'(?![A-Za-z])',

        content,

        re.I

    ):

        a_score += 5

        a_reasons.append(
            "A股ticker"
        )


    if any(

        keyword in content

        for keyword
        in A_KEYWORDS

    ):

        a_score += 3

        a_reasons.append(
            "A股关键词"
        )


    # ========================================================
    # 美股硬证据
    # ========================================================

    if re.search(

        r'\b'
        r'[A-Z]{1,6}'
        r'\.(?:O|N|A)'
        r'\b',

        content

    ):

        us_score += 5

        us_reasons.append(
            "美股ticker"
        )


    if any(

        keyword in content

        for keyword
        in US_KEYWORDS

    ):

        us_score += 3

        us_reasons.append(
            "美股关键词"
        )


    # ========================================================
    # 港股硬证据
    # ========================================================

    if re.search(

        r'(?<!\d)'
        r'\d{4,5}'
        r'\.HK'
        r'(?![A-Za-z])',

        content,

        re.I

    ):

        hk_score += 5

        hk_reasons.append(
            "港股ticker"
        )


    if any(

        keyword in content

        for keyword
        in HK_KEYWORDS

    ):

        hk_score += 3

        hk_reasons.append(
            "港股关键词"
        )


    evidence = {

        "A股": {

            "score":
                a_score,

            "reasons":
                a_reasons,

        },


        "美股": {

            "score":
                us_score,

            "reasons":
                us_reasons,

        },


        "港股": {

            "score":
                hk_score,

            "reasons":
                hk_reasons,

        },

    }


    # ========================================================
    # A股明显强
    # ========================================================

    if (
        a_score > us_score
        and a_score > 0
    ):

        return (

            "A股",

            "evidence_score",

            evidence

        )


    # ========================================================
    # 美股明显强
    # ========================================================

    if (
        us_score > a_score
        and us_score > 0
    ):

        return (

            "美股",

            "evidence_score",

            evidence

        )


    # ========================================================
    # 真正A股 + 美股双市场
    # ========================================================

    if (
        a_score >= 5
        and us_score >= 5
        and a_score == us_score
    ):

        return (

            "A股+美股",

            "dual_market",

            evidence

        )


    # ========================================================
    # 港股
    # ========================================================

    if (
        a_score == 0
        and us_score == 0
        and hk_score > 0
    ):

        return (

            "港股",

            "hk_evidence",

            {
                "港股":
                    evidence["港股"]
            }

        )


    # ========================================================
    # Unknown
    # ========================================================

    return (

        "未知/其他",

        "uncertain",

        evidence

    )


# ============================================================
# 13. 清洗新闻
# ============================================================

def clean_news_record(
    data_body
):

    classify_ids = (

        data_body.get(
            "classify",
            []
        )

        or []

    )


    classify_names = (

        resolve_classify_names(
            classify_ids
        )

    )


    # ========================================================
    # A股股票
    # ========================================================

    a_share_stocks = []


    for s in (

        data_body.get(
            "a_shares",
            []
        )

        or []

    ):


        symbol = s.get(
            "symbol"
        )


        if is_not_individual_stock(
            symbol
        ):

            continue


        a_share_stocks.append({

            "name":
                s.get(
                    "name"
                ),

            "symbol":
                symbol,

        })


    # ========================================================
    # 新闻正文
    # ========================================================

    inner_data = (

        data_body.get(
            "data",
            {}
        )

        or {}

    )


    if isinstance(
        inner_data,
        dict
    ):

        content = (

            inner_data.get(
                "content",
                ""
            )

            or ""

        )


    else:

        content = ""


    # ========================================================
    # 基础record
    # ========================================================

    record = {

        "id":
            data_body.get(
                "id"
            ),

        "time":
            data_body.get(
                "time"
            ),

        "action":
            data_body.get(
                "action"
            ),

        "content":
            content,

        "important":
            data_body.get(
                "important",
                0
            ),

        "classify_ids":
            classify_ids,

        "classify_names":
            classify_names,

        "classify_names_str":
            "|".join(
                classify_names
            ),

        "a_share_stocks":
            a_share_stocks,

    }


    # ========================================================
    # 市场重新分类
    # ========================================================

    (
        market,
        method,
        evidence

    ) = classify_stock_market(
        record
    )


    record[
        "market"
    ] = market


    record[
        "market_classification_method"
    ] = method


    record[
        "market_classification_evidence"
    ] = evidence


    return record


# ============================================================
# 14. 分类数据留底
# ============================================================

def write_classified_log(
    record
):

    market = record.get(
        "market"
    )


    if market == "A股":

        append_jsonl(
            CLASSIFIED_A_FILE,
            record
        )


    elif market == "美股":

        append_jsonl(
            CLASSIFIED_US_FILE,
            record
        )


    elif market == "港股":

        append_jsonl(
            CLASSIFIED_HK_FILE,
            record
        )


    elif market == "A股+美股":

        append_jsonl(
            CLASSIFIED_A_US_FILE,
            record
        )


    else:

        append_jsonl(
            CLASSIFIED_UNKNOWN_FILE,
            record
        )


# ============================================================
# 15. scored log
# ============================================================

def write_scored_log(
    record
):

    # --------------------------------------------------------
    # 全市场总文件
    # --------------------------------------------------------

    append_jsonl(
        SCORED_LOG_FILE,
        record
    )


    market = (

        record.get(
            "score_market"
        )

        or

        record.get(
            "market"
        )

    )


    # --------------------------------------------------------
    # Dashboard A股文件
    # --------------------------------------------------------

    if market == "A股":

        append_jsonl(
            SCORED_LOG_A_FILE,
            record
        )


    # --------------------------------------------------------
    # Dashboard 美股文件
    # --------------------------------------------------------

    elif market == "美股":

        append_jsonl(
            SCORED_LOG_US_FILE,
            record
        )


def write_unscored_live_record(
    record,
    market
):

    r = dict(
        record
    )

    r[
        "score_market"
    ] = market

    r[
        "claude_gate_triggered"
    ] = None

    r[
        "claude_reasoning"
    ] = "Claude scoring is not configured."

    r[
        "claude_score"
    ] = None

    r[
        "claude_confidence"
    ] = None

    write_scored_log(
        r
    )


# ============================================================
# 16. Claude打分
# ============================================================

def score_one_news(
    news_id,
    market,
    content,
    system_prompt
):

    if claude_client is None:
        log("[Claude错误] 缺少 ANTHROPIC_API_KEY，跳过打分。")
        return None

    news_item_json = json.dumps(

        [

            {

                "id":
                    news_id,

                "市场":
                    market,

                "新闻文本":
                    content,

            }

        ],

        ensure_ascii=False

    )


    user_message = (

        "下面是1条新闻，"
        "请按系统提示里的规则打分，"
        "严格按JSON数组格式输出"
        "（数组里只有1个对象，"
        "也要保持数组格式）：\n\n"

        f"新闻列表：\n"

        f"{news_item_json}\n"

    )


    last_error = None


    for attempt in range(

        1,

        CLAUDE_MAX_RETRIES + 1

    ):


        try:

            msg = (

                claude_client

                .messages

                .create(

                    model=
                        CLAUDE_MODEL,

                    max_tokens=
                        500,

                    system=
                        system_prompt,

                    messages=[

                        {

                            "role":
                                "user",

                            "content":
                                user_message,

                        }

                    ],

                )

            )


            raw_text = (

                msg.content[0]
                .text
                .strip()

                if msg.content

                else ""

            )


            raw = re.sub(

                r'^```json\s*|\s*```$',

                '',

                raw_text

            ).strip()


            if not raw:

                raise ValueError(
                    "Claude返回为空"
                )


            # ==================================================
            # JSON解析
            # ==================================================

            try:

                parsed = json.loads(
                    raw
                )


            except json.JSONDecodeError:

                start = raw.find(
                    "["
                )

                end = raw.rfind(
                    "]"
                )


                if (

                    start != -1

                    and end != -1

                    and end > start

                ):

                    parsed = json.loads(

                        raw[
                            start:
                            end + 1
                        ]

                    )


                else:

                    raise ValueError(
                        "未找到JSON数组"
                    )


            if (

                not isinstance(
                    parsed,
                    list
                )

                or len(parsed) != 1

            ):

                raise ValueError(

                    f"返回格式异常: "
                    f"{parsed}"

                )


            result = (
                parsed[0]
            )


            # ==================================================
            # ID校验
            # ==================================================

            if (

                result.get(
                    "id"
                )

                is not None

            ):


                if str(

                    result.get(
                        "id"
                    )

                ) != str(
                    news_id
                ):


                    raise ValueError(

                        f"id不匹配："
                        f"期望={news_id}，"
                        f"返回={result.get('id')}"

                    )


            return result


        except Exception as e:

            last_error = e


            if (

                attempt
                <
                CLAUDE_MAX_RETRIES

            ):


                wait = (

                    CLAUDE_RETRY_BACKOFF

                    *

                    (
                        2
                        **
                        (attempt - 1)
                    )

                )


                log(

                    f"[Claude警告] "
                    f"id={news_id} "
                    f"market={market} "
                    f"第{attempt}次失败: "
                    f"{e}，"
                    f"{wait}秒后重试"

                )


                time.sleep(
                    wait
                )


    log(

        f"[Claude错误] "
        f"id={news_id} "
        f"market={market} "
        f"彻底失败: "
        f"{last_error}"

    )


    return None


# ============================================================
# 17. 合并Claude结果
# ============================================================

def merge_score_result(
    record,
    market,
    score_result
):

    r = dict(
        record
    )


    r[
        "score_market"
    ] = market


    r[
        "claude_gate_triggered"
    ] = score_result.get(
        "gate_triggered"
    )


    r[
        "claude_reasoning"
    ] = score_result.get(
        "reasoning"
    )


    r[
        "claude_score"
    ] = score_result.get(
        "情绪分"
    )


    r[
        "claude_confidence"
    ] = score_result.get(
        "置信度"
    )


    return r


# ============================================================
# 18. A股处理
# ============================================================

def process_a_share(
    record
):

    news_id = record[
        "id"
    ]


    content = record.get(
        "content",
        ""
    )


    log(

        f"[处理-A股] "
        f"id={news_id}"

    )

    if claude_client is None:

        write_unscored_live_record(
            record,
            "A股"
        )

        log(

            f"[A股-已保存未打分] "
            f"id={news_id}"

        )

        return True


    score_result = score_one_news(

        news_id,

        "A股",

        content,

        SYSTEM_PROMPT_A

    )


    if not score_result:

        log(

            f"[A股打分失败] "
            f"id={news_id}"

        )

        return False


    r = merge_score_result(

        record,

        "A股",

        score_result

    )


    score = r.get(
        "claude_score"
    )


    gate = r.get(
        "claude_gate_triggered"
    )


    if score is None:

        log(

            f"[A股score缺失] "
            f"id={news_id}"

        )

        return False


    # ========================================================
    # 中性关卡
    # ========================================================

    is_neutral = (

        4 <= score <= 6

        and gate is not None

    )


    if is_neutral:


        if gate == "A":

            append_jsonl(

                GATE_A_DIGEST_FILE,

                r

            )


            log(

                f"[A股-待汇总] "
                f"id={news_id} "
                f"score={score} "
                f"gate=A"

            )


        else:

            log(

                f"[A股-丢弃] "
                f"id={news_id} "
                f"score={score} "
                f"gate={gate}"

            )


        return True


    # ========================================================
    # 有方向性
    #
    # 这里已经完全取消企业微信。
    #
    # 现在只需要写入JSONL。
    #
    # backend.py会读取这个文件。
    #
    # HTML每5秒自动读取backend。
    # ========================================================

    write_scored_log(
        r
    )


    log(

        f"[A股-已保存] "
        f"id={news_id} "
        f"score={score}"

    )


    return True


# ============================================================
# 19. 美股处理
# ============================================================

def process_us_stock(
    record
):

    news_id = record[
        "id"
    ]


    content = record.get(
        "content",
        ""
    )


    log(

        f"[处理-美股] "
        f"id={news_id}"

    )

    if claude_client is None:

        write_unscored_live_record(
            record,
            "美股"
        )

        log(

            f"[美股-已保存未打分] "
            f"id={news_id}"

        )

        return True


    score_result = score_one_news(

        news_id,

        "美股",

        content,

        SYSTEM_PROMPT_US

    )


    if not score_result:

        log(

            f"[美股打分失败] "
            f"id={news_id}"

        )

        return False


    r = merge_score_result(

        record,

        "美股",

        score_result

    )


    score = r.get(
        "claude_score"
    )


    gate = r.get(
        "claude_gate_triggered"
    )


    if score is None:

        log(

            f"[美股score缺失] "
            f"id={news_id}"

        )

        return False


    # ========================================================
    # 中性关卡
    # ========================================================

    is_neutral = (

        4 <= score <= 6

        and gate is not None

    )


    if is_neutral:


        if gate == "F":

            append_jsonl(

                US_ANALYST_DIGEST_FILE,

                r

            )


            log(

                f"[美股-分析师记录] "
                f"id={news_id} "
                f"score={score} "
                f"gate=F"

            )


        else:

            log(

                f"[美股-丢弃] "
                f"id={news_id} "
                f"score={score} "
                f"gate={gate}"

            )


        return True


    # ========================================================
    # 有方向性
    #
    # 不再发企业微信。
    #
    # 直接写入Dashboard数据文件。
    # ========================================================

    write_scored_log(
        r
    )


    log(

        f"[美股-已保存] "
        f"id={news_id} "
        f"score={score}"

    )


    return True


# ============================================================
# 20. Worker
# ============================================================

def worker_loop():

    while True:


        record = (
            news_queue.get()
        )


        try:

            news_id = str(

                record.get(
                    "id",
                    ""
                )

            )


            market = record.get(
                "market"
            )


            method = record.get(
                "market_classification_method"
            )


            log(

                f"[开始处理] "
                f"id={news_id} "
                f"market={market} "
                f"method={method}"

            )


            # ==================================================
            # A股
            # ==================================================

            if market == "A股":


                success = (
                    process_a_share(
                        record
                    )
                )


                if success:

                    mark_processed(
                        news_id
                    )


            # ==================================================
            # 美股
            # ==================================================

            elif market == "美股":


                success = (
                    process_us_stock(
                        record
                    )
                )


                if success:

                    mark_processed(
                        news_id
                    )


            # ==================================================
            # A股 + 美股
            # ==================================================

            elif market == "A股+美股":


                log(

                    f"[双市场] "
                    f"id={news_id} "
                    f"分别跑A股和美股prompt"

                )


                a_success = (
                    process_a_share(
                        dict(
                            record
                        )
                    )
                )


                us_success = (
                    process_us_stock(
                        dict(
                            record
                        )
                    )
                )


                if (

                    a_success

                    and us_success

                ):

                    mark_processed(
                        news_id
                    )


                else:

                    log(

                        f"[双市场未完全成功] "
                        f"id={news_id} "
                        f"A={a_success} "
                        f"US={us_success}"

                    )


            # ==================================================
            # 港股
            # ==================================================

            elif market == "港股":


                log(

                    f"[跳过-港股] "
                    f"id={news_id}"

                )


                mark_processed(
                    news_id
                )


            # ==================================================
            # Unknown
            # ==================================================

            else:


                log(

                    f"[跳过-未知] "
                    f"id={news_id} "
                    f"classify="
                    f"{record.get('classify_names_str','')[:100]}"

                )


                mark_processed(
                    news_id
                )


        except Exception as e:


            log(

                f"[处理异常] "
                f"id="
                f"{record.get('id','?')} "
                f"{e}"

            )


        finally:

            news_queue.task_done()


# ============================================================
# 21. WebSocket callbacks
# ============================================================

def on_open(
    ws
):

    log(
        "WebSocket已连接，"
        "发送身份验证..."
    )


    ws.send(

        json.dumps({

            "action":
                "auth",

            "params": {

                "secret-key":
                    SECRET_KEY

            }

        })

    )


def on_message(
    ws,
    message
):

    try:

        msg = json.loads(
            message
        )


    except Exception as e:

        log(

            f"消息解析失败: "
            f"{e}"

        )

        return


    msg_type = msg.get(
        "type"
    )


    # ========================================================
    # Auth
    # ========================================================

    if msg_type == "auth_result":


        if (

            msg.get(
                "data",
                {}
            ).get(
                "auth_result"
            )

            == 200

        ):


            log(

                "验证成功，"
                "发送订阅请求..."

            )


            ws.send(

                json.dumps({

                    "action":
                        "subscribe",

                    "params":
                        SUBSCRIBE_PARAMS

                })

            )


        else:


            log(

                f"验证失败: "
                f"{msg}"

            )


        return


    # ========================================================
    # Subscribe
    # ========================================================

    if msg_type == "subscribe_result":


        log(

            f"订阅结果: "
            f"{msg}"

        )


        return


    # ========================================================
    # 其他类型不处理
    # ========================================================

    if msg_type != "data":

        return


    # ========================================================
    # 新闻正文
    # ========================================================

    data_body = (

        msg.get(
            "data",
            {}
        )

        or {}

    )


    news_id = str(

        data_body.get(
            "id",
            "未知id"
        )

    )


    inner_data = (

        data_body.get(
            "data",
            {}
        )

        or {}

    )


    if isinstance(
        inner_data,
        dict
    ):


        content = (

            inner_data.get(
                "content",
                ""
            )

            or ""

        )


    else:

        content = ""


    # ========================================================
    # 原始消息永远先留底
    # ========================================================

    if LOG_RAW_MESSAGES:
        append_jsonl(

            RAW_LOG_FILE,

            msg

        )


    # ========================================================
    # 最保守内容去重
    #
    # 同一个ID + 正文完全相同才跳过
    # ========================================================

    old_content = (

        SEEN_NEWS_CONTENT.get(
            news_id
        )

    )


    if (

        old_content is not None

        and old_content == content

    ):

        return


    SEEN_NEWS_CONTENT[
        news_id
    ] = content


    # ========================================================
    # HTML汇总文章过滤
    # ========================================================

    if (

        "section-news"
        in content

        or content.count(
            "<br/>"
        ) > 3

        or content.count(
            "<br>"
        ) > 3

    ):


        log(

            f"[跳过-HTML汇总] "
            f"id={news_id}"

        )


        return


    # ========================================================
    # 清洗 + 市场分类
    # ========================================================

    record = clean_news_record(
        data_body
    )


    # ========================================================
    # clean留底
    # ========================================================

    append_jsonl(

        CLEAN_LOG_FILE,

        record

    )


    # ========================================================
    # 按最终市场分类留底
    # ========================================================

    write_classified_log(
        record
    )


    # ========================================================
    # 已经完整处理过
    # ========================================================

    if news_id in PROCESSED_IDS:


        log(

            f"[跳过-已处理] "
            f"id={news_id}"

        )


        return


    # ========================================================
    # 日志
    # ========================================================

    log(

        f"[收到新闻] "
        f"id={news_id} "
        f"市场={record.get('market')} "
        f"方法="
        f"{record.get('market_classification_method')} "
        f"classify="
        f"{record.get('classify_names_str','')[:70]} "
        f"内容="
        f"{content[:70]}"

    )


    # ========================================================
    # 入Claude worker队列
    # ========================================================

    news_queue.put(
        record
    )


def on_error(
    ws,
    error
):

    log(

        f"WebSocket错误: "
        f"{error}"

    )


def on_close(
    ws,
    code,
    msg
):

    log(

        f"WebSocket关闭: "
        f"code={code}, "
        f"msg={msg}"

    )


# ============================================================
# 22. WebSocket自动重连
# ============================================================

def run_websocket_forever():

    while True:


        try:


            ws = (

                websocket

                .WebSocketApp(

                    WS_URL,

                    on_open=
                        on_open,

                    on_message=
                        on_message,

                    on_error=
                        on_error,

                    on_close=
                        on_close,

                )

            )


            ws.run_forever(

                ping_interval=15,

                ping_timeout=8

            )


        except KeyboardInterrupt:


            log(

                "收到Ctrl+C，"
                "程序退出"

            )


            break


        except Exception as e:


            log(

                f"WebSocket主循环异常: "
                f"{e}"

            )


        log(

            f"连接断开，"
            f"{RECONNECT_WAIT_SEC}"
            f"秒后自动重连..."

        )


        time.sleep(
            RECONNECT_WAIT_SEC
        )


# ============================================================
# 23. 主程序
# ============================================================

def main():

    global CLASSIFY_ID_TO_NAME

    global PROCESSED_IDS

    if not SECRET_KEY:
        log("缺少 JIN10_SECRET_KEY，Daily Summary collector 不启动。")
        return

    log(
        "=" * 70
    )


    score_mode = "Claude打分" if claude_client is not None else "未打分实时流"

    log(

        f"启动：A股 / 美股 / 港股 实时新闻分类 + {score_mode} + Dashboard流水线"

    )


    log(

        "分类父标签："
        "29=A股 / "
        "27=美股 / "
        "28=港股"

    )


    log(

        "优先级："
        "A+港→A，"
        "美+港→美，"
        "A+美→硬证据裁决，"
        "无法确认→unknown"

    )


    log(

        "输出方式："
        "JSONL → backend.py → HTML Dashboard"

    )


    log(

        "企业微信推送：已关闭"

    )


    # ========================================================
    # classify map
    # ========================================================

    try:


        log(

            "拉取classify映射表..."

        )


        CLASSIFY_ID_TO_NAME = (

            fetch_classify_map()

        )


        log(

            f"classify映射成功："
            f"{len(CLASSIFY_ID_TO_NAME)} "
            f"个分类"

        )


    except Exception as e:


        log(

            f"[警告] "
            f"在线拉取失败: "
            f"{e}"

        )


        log(

            "尝试读取本地缓存..."

        )


        CLASSIFY_ID_TO_NAME = (

            load_cached_classify_map()

        )


        if CLASSIFY_ID_TO_NAME:


            log(

                f"本地缓存成功："
                f"{len(CLASSIFY_ID_TO_NAME)} "
                f"个分类"

            )


        else:


            log(

                "没有classify缓存，"
                "使用空映射继续。"
                "父分类ID仍然可以正常工作。"

            )


    # ========================================================
    # 恢复历史状态
    # ========================================================

    log(

        "恢复历史处理状态..."

    )


    PROCESSED_IDS = (

        load_processed_ids()

    )


    rebuild_seen_content_from_log()


    log(

        f"已完整处理："
        f"{len(PROCESSED_IDS)} 条"

    )


    log(

        f"内容去重记忆："
        f"{len(SEEN_NEWS_CONTENT)} 条"

    )


    # ========================================================
    # Worker
    # ========================================================

    worker_thread = (

        threading.Thread(

            target=
                worker_loop,

            daemon=
                True

        )

    )


    worker_thread.start()


    log(

        "处理线程已启动"

    )


    # ========================================================
    # WebSocket
    # ========================================================

    log(

        f"启动WebSocket，"
        f"订阅category="
        f"{SUBSCRIBE_PARAMS['category']}"

    )


    run_websocket_forever()


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":

    main()
