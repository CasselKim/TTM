from enum import StrEnum


class OrderSide(StrEnum):
    """주문 방향"""

    BID = "bid"  # 매수
    ASK = "ask"  # 매도


class OrderType(StrEnum):
    """주문 타입"""

    LIMIT = "limit"  # 지정가
    PRICE = "price"  # 시장가 매수
    MARKET = "market"  # 시장가 매도


class TradingAction(StrEnum):
    """거래 액션"""

    BUY = "BUY"  # 매수
    SELL = "SELL"  # 매도
    HOLD = "HOLD"  # 보유


class DcaStatus(StrEnum):
    """DCA 실행 상태"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class DcaPhase(StrEnum):
    """DCA 단계"""

    INACTIVE = "inactive"  # 비활성 상태
    INITIAL_BUY = "initial_buy"  # 초기 매수 단계
    ACCUMULATING = "accumulating"  # 추가 매수(물타기) 단계
    PROFIT_TAKING = "profit_taking"  # 익절 대기 단계
    FORCE_SELLING = "force_selling"  # 강제 손절 단계


class CycleStatus(StrEnum):
    """사이클 상태"""

    COMPLETED = "completed"
    FAILED = "failed"
    FORCE_STOPPED = "force_stopped"


class ActionTaken(StrEnum):
    """수행된 액션"""

    START = "start"
    STOP = "stop"
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXECUTE = "execute"


# ==========================================================
# OrderState Enum
# ==========================================================


class OrderState(StrEnum):
    """주문 상태"""

    WAIT = "wait"  # 대기
    WATCH = "watch"  # 모니터링 중
    DONE = "done"  # 완료(체결)
    CANCEL = "cancel"  # 취소


# ==========================================================
# Currency Enum
# ==========================================================


class Currency(StrEnum):
    """지원 통화"""

    INCH = "1INCH"  # 1INCH
    A = "A"  # A
    AAVE = "AAVE"  # AAVE
    ACM = "ACM"  # ACM
    ACS = "ACS"  # ACS
    ADA = "ADA"  # 에이다
    AERGO = "AERGO"  # AERGO
    AFC = "AFC"  # AFC
    AGLD = "AGLD"  # AGLD
    AHT = "AHT"  # AHT
    AKT = "AKT"  # AKT
    ALGO = "ALGO"  # ALGO
    ALT = "ALT"  # ALT
    ANIME = "ANIME"  # ANIME
    ANKR = "ANKR"  # ANKR
    APE = "APE"  # APE
    API3 = "API3"  # API3
    APT = "APT"  # APT
    AQT = "AQT"  # AQT
    ARB = "ARB"  # ARB
    ARDR = "ARDR"  # ARDR
    ARK = "ARK"  # ARK
    ARKM = "ARKM"  # ARKM
    ARPA = "ARPA"  # ARPA
    ASTR = "ASTR"  # ASTR
    ATH = "ATH"  # ATH
    ATM = "ATM"  # ATM
    ATOM = "ATOM"  # ATOM
    AUCTION = "AUCTION"  # AUCTION
    AUDIO = "AUDIO"  # AUDIO
    AVAX = "AVAX"  # AVAX
    AWE = "AWE"  # AWE
    AXL = "AXL"  # AXL
    AXS = "AXS"  # AXS
    BAR = "BAR"  # BAR
    BAT = "BAT"  # BAT
    BCH = "BCH"  # 비트코인캐시
    BEAM = "BEAM"  # BEAM
    BERA = "BERA"  # BERA
    BFC = "BFC"  # BFC
    BIGTIME = "BIGTIME"  # BIGTIME
    BLAST = "BLAST"  # BLAST
    BLUR = "BLUR"  # BLUR
    BNT = "BNT"  # BNT
    BONK = "BONK"  # BONK
    BORA = "BORA"  # BORA
    BOUNTY = "BOUNTY"  # BOUNTY
    BRETT = "BRETT"  # BRETT
    BSV = "BSV"  # BSV
    BTC = "BTC"  # 비트코인
    BTT = "BTT"  # BTT
    CARV = "CARV"  # CARV
    CBK = "CBK"  # CBK
    CELO = "CELO"  # CELO
    CHR = "CHR"  # CHR
    CHZ = "CHZ"  # CHZ
    CITY = "CITY"  # CITY
    CKB = "CKB"  # CKB
    COMP = "COMP"  # COMP
    COW = "COW"  # COW
    CRO = "CRO"  # CRO
    CRV = "CRV"  # CRV
    CTC = "CTC"  # CTC
    CTSI = "CTSI"  # CTSI
    CVC = "CVC"  # CVC
    CYBER = "CYBER"  # CYBER
    DEEP = "DEEP"  # DEEP
    DENT = "DENT"  # DENT
    DGB = "DGB"  # DGB
    DKA = "DKA"  # DKA
    DNT = "DNT"  # DNT
    DOGE = "DOGE"  # 도지코인
    DOT = "DOT"  # 폴카닷
    DRIFT = "DRIFT"  # DRIFT
    EGLD = "EGLD"  # EGLD
    ELF = "ELF"  # ELF
    ENJ = "ENJ"  # ENJ
    ENS = "ENS"  # ENS
    EPT = "EPT"  # EPT
    ETC = "ETC"  # ETC
    ETH = "ETH"  # 이더리움
    FCT2 = "FCT2"  # FCT2
    FIL = "FIL"  # FIL
    FLOCK = "FLOCK"  # FLOCK
    FLOW = "FLOW"  # FLOW
    FORT = "FORT"  # FORT
    G = "G"  # G
    GAME2 = "GAME2"  # GAME2
    GAS = "GAS"  # GAS
    GLM = "GLM"  # GLM
    GLMR = "GLMR"  # GLMR
    GMT = "GMT"  # GMT
    GO = "GO"  # GO
    GRS = "GRS"  # GRS
    GRT = "GRT"  # GRT
    GTC = "GTC"  # GTC
    HBAR = "HBAR"  # HBAR
    HBD = "HBD"  # HBD
    HIVE = "HIVE"  # HIVE
    HP = "HP"  # HP
    HUNT = "HUNT"  # HUNT
    HYPER = "HYPER"  # HYPER
    ICX = "ICX"  # ICX
    ID = "ID"  # ID
    IMX = "IMX"  # IMX
    INJ = "INJ"  # INJ
    INTER = "INTER"  # INTER
    IO = "IO"  # IO
    IOST = "IOST"  # IOST
    IOTA = "IOTA"  # IOTA
    IOTX = "IOTX"  # IOTX
    IQ = "IQ"  # IQ
    JASMY = "JASMY"  # JASMY
    JST = "JST"  # JST
    JTO = "JTO"  # JTO
    JUP = "JUP"  # JUP
    JUV = "JUV"  # JUV
    KAITO = "KAITO"  # KAITO
    KAVA = "KAVA"  # KAVA
    KERNEL = "KERNEL"  # KERNEL
    KNC = "KNC"  # KNC
    KRW = "KRW"  # 원화
    LA = "LA"  # LA
    LAYER = "LAYER"  # LAYER
    LINK = "LINK"  # 링크
    LPT = "LPT"  # LPT
    LRC = "LRC"  # LRC
    LSK = "LSK"  # LSK
    LWA = "LWA"  # LWA
    MAGIC = "MAGIC"  # MAGIC
    MANA = "MANA"  # MANA
    MASK = "MASK"  # MASK
    MBL = "MBL"  # MBL
    ME = "ME"  # ME
    MED = "MED"  # MED
    META = "META"  # META
    MEW = "MEW"  # MEW
    MINA = "MINA"  # MINA
    MLK = "MLK"  # MLK
    MNT = "MNT"  # MNT
    MOC = "MOC"  # MOC
    MOCA = "MOCA"  # MOCA
    MOVE = "MOVE"  # MOVE
    MTL = "MTL"  # MTL
    MVL = "MVL"  # MVL
    NAP = "NAP"  # NAP
    NCT = "NCT"  # NCT
    NEAR = "NEAR"  # NEAR
    NEO = "NEO"  # NEO
    NKN = "NKN"  # NKN
    NMR = "NMR"  # NMR
    NXPC = "NXPC"  # NXPC
    OAS = "OAS"  # OAS
    OBSR = "OBSR"  # OBSR
    OCEAN = "OCEAN"  # OCEAN
    OGN = "OGN"  # OGN
    OM = "OM"  # OM
    OMNI = "OMNI"  # OMNI
    ONDO = "ONDO"  # ONDO
    ONG = "ONG"  # ONG
    ONT = "ONT"  # ONT
    ORBS = "ORBS"  # ORBS
    ORCA = "ORCA"  # ORCA
    OXT = "OXT"  # OXT
    PENDLE = "PENDLE"  # PENDLE
    PENGU = "PENGU"  # PENGU
    PEPE = "PEPE"  # PEPE
    POKT = "POKT"  # POKT
    POL = "POL"  # POL
    POLYX = "POLYX"  # POLYX
    POWR = "POWR"  # POWR
    PROM = "PROM"  # PROM
    PSG = "PSG"  # PSG
    PUFFER = "PUFFER"  # PUFFER
    PUNDIAI = "PUNDIAI"  # PUNDIAI
    PUNDIX = "PUNDIX"  # PUNDIX
    PYTH = "PYTH"  # PYTH
    QKC = "QKC"  # QKC
    QTCON = "QTCON"  # QTCON
    QTUM = "QTUM"  # QTUM
    RAD = "RAD"  # RAD
    RAY = "RAY"  # RAY
    RED = "RED"  # RED
    REI = "REI"  # REI
    RENDER = "RENDER"  # RENDER
    RLC = "RLC"  # RLC
    RLY = "RLY"  # RLY
    RSR = "RSR"  # RSR
    RVN = "RVN"  # RVN
    SAFE = "SAFE"  # SAFE
    SAND = "SAND"  # SAND
    SC = "SC"  # SC
    SCR = "SCR"  # SCR
    SEI = "SEI"  # SEI
    SHELL = "SHELL"  # SHELL
    SHIB = "SHIB"  # SHIB
    SIGN = "SIGN"  # SIGN
    SKY = "SKY"  # SKY
    SNT = "SNT"  # SNT
    SNX = "SNX"  # SNX
    SOL = "SOL"  # 솔라나
    SONIC = "SONIC"  # SONIC
    SOON = "SOON"  # SOON
    SOPH = "SOPH"  # SOPH
    SPURS = "SPURS"  # SPURS
    STEEM = "STEEM"  # STEEM
    STG = "STG"  # STG
    STMX = "STMX"  # STMX
    STORJ = "STORJ"  # STORJ
    STRAX = "STRAX"  # STRAX
    STRIKE = "STRIKE"  # STRIKE
    STX = "STX"  # STX
    SUI = "SUI"  # SUI
    SUN = "SUN"  # SUN
    SWELL = "SWELL"  # SWELL
    SXP = "SXP"  # SXP
    T = "T"  # T
    TAIKO = "TAIKO"  # TAIKO
    TFUEL = "TFUEL"  # TFUEL
    THETA = "THETA"  # THETA
    TIA = "TIA"  # TIA
    TOKAMAK = "TOKAMAK"  # TOKAMAK
    TRUMP = "TRUMP"  # TRUMP
    TRX = "TRX"  # TRX
    TT = "TT"  # TT
    TUSD = "TUSD"  # TUSD
    UNI = "UNI"  # UNI
    USDC = "USDC"  # USD코인
    USDP = "USDP"  # USDP
    USDS = "USDS"  # USDS
    USDT = "USDT"  # 테더
    UXLINK = "UXLINK"  # UXLINK
    VAL = "VAL"  # VAL
    VANA = "VANA"  # VANA
    VET = "VET"  # VET
    VIRTUAL = "VIRTUAL"  # VIRTUAL
    VTHO = "VTHO"  # VTHO
    W = "W"  # W
    WAL = "WAL"  # WAL
    WAVES = "WAVES"  # WAVES
    WAXP = "WAXP"  # WAXP
    WCT = "WCT"  # WCT
    XEC = "XEC"  # XEC
    XEM = "XEM"  # XEM
    XLM = "XLM"  # 스텔라
    XRP = "XRP"  # 리플
    XTZ = "XTZ"  # XTZ
    YGG = "YGG"  # YGG
    ZETA = "ZETA"  # ZETA
    ZIL = "ZIL"  # ZIL
    ZRO = "ZRO"  # ZRO
    ZRX = "ZRX"  # ZRX
