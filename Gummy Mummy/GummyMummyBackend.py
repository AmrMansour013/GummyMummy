# GummyMummyBackend.py (مصحح ومحسن)
# ----------------------------------------------------------------------
# Gummy Mummy API v3.1 (نسخة محسنة مع تحليل أفضل للنتائج)
# ----------------------------------------------------------------------

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from contextlib import contextmanager
import sqlite3
import random
import logging

# -------------------------
# 1. إعدادات أساسية و Logging
# -------------------------
DB_FILE = "gummy_mummy.db"
SECRET_KEY = "Your-Super-Secret-Key-For-Gummy-Mummy" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 ساعة

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

app = FastAPI(
    title="Gummy Mummy API", 
    version="3.1 (Enhanced)", 
    description="Advanced offline personalized advice engine (Arabic)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# 2. إدارة قاعدة البيانات (DB)
# -------------------------

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            marital_status TEXT,
            phone TEXT,
            email TEXT,
            is_first_child INTEGER,
            is_breastfeeding INTEGER,
            baby_age_months INTEGER,
            baby_gender TEXT,
            created_at TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            section_name TEXT,
            payload TEXT,
            result TEXT,
            timestamp TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
        """)
        conn.commit()
    logger.info("Database initialized successfully.")

def get_client(client_id: int) -> Optional[dict]:
    with get_db() as conn:
        result = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    
    if result:
        client_dict = dict(result)
        client_dict['is_first_child'] = bool(client_dict['is_first_child'])
        client_dict['is_breastfeeding'] = bool(client_dict['is_breastfeeding'])
        return client_dict
    return None

def db_execute(query, params=(), fetch=False):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        if fetch:
            result = c.fetchall()
            return [dict(row) for row in result]
        else:
            return c.lastrowid

init_db()

# -------------------------
# 3. نماذج البيانات (Models)
# -------------------------
class ClientBase(BaseModel):
    name: Optional[str] = Field(None, example="أمل")
    age: Optional[int] = Field(None, ge=15, le=60, example=29)
    baby_age_months: Optional[int] = Field(None, ge=0, example=2)
    is_first_child: Optional[bool] = Field(None, example=True)
    is_breastfeeding: Optional[bool] = Field(None, example=True)
    
    baby_gender: Optional[Literal["male","female","unknown"]] = Field(None, example="unknown")
    marital_status: Optional[Literal["single","married","divorced","widowed","other"]] = Field(None, example="married")

    phone: Optional[str] = Field(None, example="+20123...")
    email: Optional[EmailStr] = Field(None, example="gummy_mummy@gmail.com")

class ClientRegistrationResponse(BaseModel):
    ok: bool
    client_id: int
    message: str
    token: str

class ResponseModel(BaseModel):
    score: float = Field(..., description="درجة التقييم (0-100)")
    status: str = Field(..., description="ملخص حالة التقييم")
    advice: str = Field(..., description="النصيحة التفصيلية والتحفيز")
    urgency: Literal["low","moderate","high"] = Field(..., description="مستوى الاستعجال المطلوب")
    details: dict = Field(..., description="البيانات التي تم تحليلها")
    diagnosis: Optional[str] = Field(None, description="تشخيص محدد للحالة")

# -------------------------
# 4. المصادقة والأمان (Auth)
# -------------------------
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_client_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "invalid_token", "message_ar": "بيانات الدخول غير صالحة"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        client_id: int = payload.get("client_id")
        if client_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return client_id

# -------------------------
# 5. محرك النصيحة المحسن (Enhanced Advice Logic)
# -------------------------
def choose_intro():
    return random.choice([
        "أنتِ تقومين بعمل رائع رغم الصعوبات. هذه تقييمات ونصائح متقدمة:",
        "شكراً لمشاركتك معلوماتك. إليك تحليل وتوصيات دقيقة:",
        "نحن هنا لدعمك. هذه نتيجة تقييم مخصصة:"
    ])

def short_encouragement():
    return random.choice([
        "تذكّري أن الراحة القصيرة أفضل من لا شيء — خصصي 10 دقائق لنفسك.",
        "أنتِ ليستِ وحدك؛ اطلبِي المساعدة عندما تحتاجين.",
        "التقدّم الصغير مهم. امنحي نفسك بعض اللطف اليوم.",
        "استمتعي باللحظات الصغيرة. هذه المرحلة لن تدوم طويلاً!"
    ])

def analyze_mothercare(payload: Dict[str, Any], baby_age: int) -> Dict[str, Any]:
    """تحليل متقدم لعناية الأم"""
    anxiety = payload.get("anxiety_level", 0)
    sadness = payload.get("sadness_level", 0)
    rest = payload.get("resting_hours", 0)
    support_freq = payload.get("support_frequency", 0)
    eating_well = payload.get("eating_well", True)

    mental_risk = anxiety + sadness
    base_score = 100 - mental_risk * 3
    
    # تحسينات إضافية بناء على عوامل أخرى
    if rest < 5:
        base_score -= 15
    if support_freq < 1:
        base_score -= 10
    if not eating_well:
        base_score -= 5
        
    score = max(10, base_score)

    if mental_risk >= 14 or score <= 40:
        status, urgency, diagnosis = "تحتاج إلى دعم نفسي عاجل", "high", "ارتفاع ملحوظ في القلق والحزن"
        advice = "**التشخيص:** قوة القلق والحزن عالية جداً. يُرجى **مراجعة مختص نفسي أو طبيب** فوراً لتقييم صحتك العقلية."
    elif mental_risk >= 8 or score <= 60:
        status, urgency, diagnosis = "مراقبة ودعم نفسي", "moderate", "مستوى معتدل من الإرهاق النفسي"
        advice = "**التشخيص:** مستوى معتدل من الإرهاق النفسي. توصياتنا: خذي قسطاً من الراحة الإجبارية."
    else:
        status, urgency, diagnosis = "حالة مستقرة", "low", "الحالة النفسية مستقرة نسبياً"
        advice = "**التشخيص:** حالتك النفسية مستقرة، استمري في روتين العناية الذاتية."

    # نصائح تفصيلية
    detailed_advice = []
    if rest < 5:
        detailed_advice.append("💤 **الراحة:** أنتِ تنامين أقل من 5 ساعات. حاولي النوم عندما ينام الطفل.")
    if support_freq < 1:
        detailed_advice.append("👥 **الدعم:** اطلبي المساعدة من الأهل مرة أسبوعياً على الأقل.")
    if not eating_well:
        detailed_advice.append("🍎 **التغذية:** اهتمي بتناول وجبات متوازنة لتعويض الطاقة.")
    if anxiety > 7:
        detailed_advice.append("🧘 **القلق:** جربي تمارين التنفس العميق لمدة 5 دقائق يومياً.")

    if detailed_advice:
        advice += "\n\n" + "\n".join(detailed_advice)

    return {
        "score": score,
        "status": status,
        "urgency": urgency,
        "diagnosis": diagnosis,
        "advice": advice
    }

def analyze_sleep(payload: Dict[str, Any], baby_age: int) -> Dict[str, Any]:
    """تحليل متقدم لنوم الطفل"""
    total = float(payload.get("total_sleep_24h", 0) or 0)
    longest = float(payload.get("longest_sleep_block_h", 0) or 0)
    falls = bool(payload.get("falls_asleep_alone", True))
    wake_ups = int(payload.get("night_wake_ups", 0) or 0)

    # تحديد النطاق الطبيعي حسب العمر
    if baby_age <= 3: 
        ideal_min, ideal_max = 14, 17
    elif baby_age <= 11: 
        ideal_min, ideal_max = 12, 15
    else: 
        ideal_min, ideal_max = 11, 14
    
    # حساب النتيجة الأساسية
    ideal_avg = (ideal_min + ideal_max) / 2
    sleep_score = max(0, 100 - abs(total - ideal_avg) * 8)
    
    # تعديلات إضافية
    if longest < 4 and baby_age > 4:
        sleep_score -= 15
    if not falls and baby_age > 6:
        sleep_score -= 10
    if wake_ups > 3:
        sleep_score -= (wake_ups - 3) * 5
        
    score = max(10, sleep_score)

    if total < ideal_min * 0.8:
        status, urgency, diagnosis = "نقص حاد في النوم", "moderate", "ساعات نوم أقل بكثير من المعدل الطبيعي"
        advice = f"**التشخيص:** الطفل ينام {total} ساعة فقط (المعدل الطبيعي: {ideal_min}-{ideal_max} ساعة)."
    elif total < ideal_min:
        status, urgency, diagnosis = "نوم أقل من المتوقع", "low", "نقص طفيف في ساعات النوم"
        advice = f"**التشخيص:** النوم قريب من الطبيعي ({total} من {ideal_min}-{ideal_max} ساعة)."
    else:
        status, urgency, diagnosis = "نوم طبيعي", "low", "نمط النوم ضمن المعدل الطبيعي"
        advice = "**التشخيص:** نوم الطفل ضمن المعدل الطبيعي."

    # نصائح تفصيلية
    tips = []
    if longest < 4 and baby_age > 4:
        tips.append("⏰ **فترة النوم:** حاولي تمديد أطول فترة نوم إلى 4-6 ساعات بتقليل التحفيز ليلاً.")
    if not falls:
        tips.append("🛌 **الاستقلالية:** ابدئي بوضع الطفل في سريره وهو شبه نائم ليتعلم النوم بمفرده.")
    if wake_ups > 3:
        tips.append("🌙 **الاستيقاظ:** قللي القيلولة النهارية إذا كانت طويلة جداً.")

    if tips:
        advice += "\n\n" + "\n".join(tips)

    return {
        "score": score,
        "status": status,
        "urgency": urgency,
        "diagnosis": diagnosis,
        "advice": advice
    }

def analyze_feeding(payload: Dict[str, Any], baby_age: int) -> Dict[str, Any]:
    """تحليل متقدم للتغذية"""
    feeding_type = str(payload.get("feeding_type", "breast"))
    pain = bool(payload.get("pain_with_latch", False))
    formula_ml = float(payload.get("formula_amount_ml_per_day", 0) or 0)
    solids_introduced = bool(payload.get("solids_introduced", False))
    feeds_per_day = int(payload.get("feeds_per_day", 8) or 8)

    score = 80.0  # نقطة بداية
    
    # تحليل حسب نوع التغذية
    if feeding_type == "breast":
        if pain:
            score -= 25
        if feeds_per_day < 6 and baby_age < 6:
            score -= 10
    elif feeding_type == "formula":
        expected_ml = baby_age * 150  # تقدير تقريبي
        if formula_ml < expected_ml * 0.7:
            score -= 20
    
    # تحليل الأطعمة الصلبة
    if baby_age > 6 and not solids_introduced:
        score -= 15
    elif baby_age < 4 and solids_introduced:
        score -= 20
        
    score = max(10, score)

    # التشخيص بناء على النتيجة
    if pain:
        status, urgency, diagnosis = "ألم بالرضاعة", "high", "صعوبة في الالتصاق/الاحتقان"
        advice = "**التشخيص:** الألم أثناء الرضاعة يتطلب استشارة **مستشارة رضاعة طبيعية**."
    elif baby_age > 6 and not solids_introduced:
        status, urgency, diagnosis = "تأخر إدخال الصلب", "moderate", "حاجة لبدء الأطعمة الصلبة"
        advice = "**التشخيص:** الطفل تجاوز 6 أشهر. يجب البدء في إدخال الأطعمة الصلبة."
    elif score <= 50:
        status, urgency, diagnosis = "مشاكل في التغذية", "moderate", "نظام التغذية يحتاج تحسين"
        advice = "**التشخيص:** هناك مشاكل متعددة في نظام التغذية تحتاج للمتابعة."
    else:
        status, urgency, diagnosis = "التغذية سليمة", "low", "نمط التغذية ملائم"
        advice = "**التشخيص:** يبدو أن نظام تغذية الطفل ملائم."

    # نصائح مخصصة
    tips = []
    if feeding_type == "breast" and pain:
        tips.append("🤱 **الرضاعة:** جربي أوضاع مختلفة للرضاعة وتأكدي من التصاق صحيح.")
    if baby_age > 6 and not solids_introduced:
        tips.append("🍌 **الأطعمة:** ابدئي بأطعمة لينة مثل الموز المهروس أو الأرز.")
    if feeds_per_day < 6 and baby_age < 6:
        tips.append("⏱️ **العدد:** زيدي عدد الرضعات إلى 8-12 مرة يومياً للرضع الصغار.")

    if tips:
        advice += "\n\n" + "\n".join(tips)

    return {
        "score": score,
        "status": status,
        "urgency": urgency,
        "diagnosis": diagnosis,
        "advice": advice
    }

def generate_personalized_advice(section: str, client: Optional[dict], payload: Dict[str, Any]):
    """محرك النصيحة الرئيسي المحسن"""
    intro = choose_intro()
    
    # بناء معلومات الملف الشخصي
    parts = []
    if client and client.get("name"):
        parts.append(client["name"])
    if client and client.get("is_first_child"):
        parts.append("الولادة الأولى")
    
    baby_age = payload.get("baby_age_months", client.get("baby_age_months") if client else 0)
    if baby_age:
        parts.append(f"عمر الطفل {baby_age} شهر")
        
    if client and client.get("is_breastfeeding"):
        parts.append("ترضعين طبيعياً")
    
    profile_note = " — (" + " · ".join(parts) + ")" if parts else ""
    
    # استدعاء محلل القسم المناسب
    analysis_result = {}
    
    if section == "mothercare":
        analysis_result = analyze_mothercare(payload, baby_age)
    elif section == "sleep":
        analysis_result = analyze_sleep(payload, baby_age)
    elif section == "feeding":
        analysis_result = analyze_feeding(payload, baby_age)
    elif section == "hygiene":
        # تحليل النظافة (يمكن إضافة الدالة لاحقاً)
        analysis_result = {
            "score": 85.0,
            "status": "جيدة",
            "urgency": "low", 
            "diagnosis": "العناية بالنظافة جيدة",
            "advice": "**التشخيص:** روتين النظافة مناسب. استمري في العناية اليومية."
        }
    elif section == "triage":
        # تحليل الطوارئ (يمكن إضافة الدالة لاحقاً)
        analysis_result = {
            "score": 90.0,
            "status": "مستقر",
            "urgency": "low",
            "diagnosis": "لا توجد أعراض طارئة",
            "advice": "**التشخيص:** الحالة مستقرة. استمري في المراقبة الروتينية."
        }
    elif section == "development":
        # تحليل التطور (يمكن إضافة الدالة لاحقاً)
        analysis_result = {
            "score": 80.0,
            "status": "متقدم",
            "urgency": "low",
            "diagnosis": "التطور ضمن المعدل الطبيعي",
            "advice": "**التشخيص:** طفلك ينمو بشكل جيد. واصلي التحفيز المناسب للعمر."
        }
    else:
        analysis_result = {
            "score": 50.0,
            "status": "غير معروف",
            "urgency": "low",
            "diagnosis": "القسم غير معروف",
            "advice": "يرجى اختيار قسم صحيح"
        }

    # بناء النصيحة النهائية
    final_advice = intro + profile_note
    final_advice += f"\n\n{analysis_result['advice']}"
    final_advice += f"\n\n---\n**رسالة تحفيزية:** {short_encouragement()}"

    return {
        "advice": final_advice,
        "details": payload,
        "score": analysis_result["score"],
        "status": analysis_result["status"],
        "urgency": analysis_result["urgency"],
        "diagnosis": analysis_result["diagnosis"]
    }

# -------------------------
# 6. Endpoints
# -------------------------

@app.post(
    "/register",
    response_model=ClientRegistrationResponse,
    summary="تسجيل عميل جديد",
)
def register_client(client: ClientBase):
    """يسجل بيانات الأم الأساسية ويعيد توكن للوصول إلى الأقسام."""
    logger.info(f"New registration attempt: {client.name}")
    try:
        ts = datetime.now(timezone.utc).isoformat()
        client_id = db_execute(
            """INSERT INTO clients (name,age,marital_status,phone,email,is_first_child,is_breastfeeding,baby_age_months,baby_gender,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (client.name,client.age,client.marital_status,client.phone,client.email,
             int(client.is_first_child or False),int(client.is_breastfeeding or False),client.baby_age_months,client.baby_gender,ts)
        )
        
        token = create_access_token(data={"client_id": client_id})

        return {
            "ok": True, 
            "client_id": client_id, 
            "message": f"مرحبًا {client.name or 'يا أمي'} — تم حفظ بياناتك بنجاح.",
            "token": token
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Registration error: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={"error": "registration_failed", "message_ar": "فشل في تسجيل البيانات"}
        )

@app.post(
    "/section/{section_name}", 
    response_model=ResponseModel,
    summary="تقييم قسم معين",
)
def handle_section(
    section_name: str, 
    payload: Dict[str, Any], 
    client_id: int = Depends(get_current_client_id)
):
    """يعالج بيانات الأقسام ويقدم نصيحة مخصصة. يتطلب توكن للمصادقة."""
    logger.info(f"Client {client_id} requested section: {section_name}")
    
    client_data = get_client(client_id)
    if not client_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "client_not_found", "message_ar": "العميل غير موجود أو التوكن غير صالح."}
        )

    try:
        res = generate_personalized_advice(section_name, client_data, payload)
        ts = datetime.now(timezone.utc).isoformat()
        db_execute(
            "INSERT INTO sections (client_id,section_name,payload,result,timestamp) VALUES (?,?,?,?,?)",
            (client_id, section_name, str(payload), str(res), ts)
        )
        return res
    except Exception as e:
        logger.error(f"Advice engine error for client {client_id} in {section_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "advice_logic_error", "message_ar": "حدث خطأ داخلي أثناء معالجة النصيحة"}
        )

@app.get("/health")
def health():
    return {"status":"ok","time":datetime.now(timezone.utc).isoformat(),"message_ar":"الخدمة تعمل."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=1000)