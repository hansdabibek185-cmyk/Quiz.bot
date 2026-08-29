import logging
import random
import asyncio
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8395594186:AAHD2d4eMv4teTbIVAnujzZtrW7AHGqsy3U"
ADMIN_ID = 5699359348

# --- DATABASE SETUP FOR LARGE SCALE ---
def init_db():
    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    # Users table for wallets & verification status
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            wallet INTEGER DEFAULT 100,
            verified INTEGER DEFAULT 0
        )
    """)
    # Leaderboard table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            score INTEGER,
            tier TEXT
        )
    """)
    # Platform stats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY,
            total_collected INTEGER DEFAULT 0,
            total_payouts INTEGER DEFAULT 0,
            house_earnings INTEGER DEFAULT 0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO stats (id, total_collected, total_payouts, house_earnings) VALUES (1, 0, 0, 0)")
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect("quiz_bot.db")
    conn.row_factory = sqlite3.Row
    return conn

user_sessions = {} # Active game sessions in memory

# --- EXTENSIVE UNIQUE QUESTION POOL ---
def generate_questions():
    pool = {"tier_1": [], "tier_2": [], "tier_3": []}
    
    tier1_data = [
        ("Bharat ki rajdhani (Capital) kya hai?", ["New Delhi", "Mumbai", "Kolkata", "Chennai"], "New Delhi"),
        ("Japan ki rajdhani kahan hai?", ["Tokyo", "Kyoto", "Osaka", "Hiroshima"], "Tokyo"),
        ("France ki rajdhani kya hai?", ["Paris", "Lyon", "Marseille", "Nice"], "Paris"),
        ("Australia ki rajdhani kya hai?", ["Canberra", "Sydney", "Melbourne", "Perth"], "Canberra"),
        ("Canada ki rajdhani kaun si hai?", ["Ottawa", "Toronto", "Vancouver", "Montreal"], "Ottawa"),
        ("Egypt ki rajdhani kya hai?", ["Cairo", "Alexandria", "Giza", "Luxor"], "Cairo"),
        ("Italy ki rajdhani kya hai?", ["Rome", "Milan", "Venice", "Florence"], "Rome"),
        ("Germany ki rajdhani kya hai?", ["Berlin", "Munich", "Frankfurt", "Hamburg"], "Berlin"),
        ("Taj Mahal kis nadi ke kinare sthit hai?", ["Yamuna", "Ganga", "Brahmaputra", "Narmada"], "Yamuna"),
        ("Bharat ki sabse lambi nadi kaun si hai?", ["Ganga", "Yamuna", "Godavari", "Brahmaputra"], "Ganga"),
        ("Qutub Minar kahan sthit hai?", ["Delhi", "Agra", "Jaipur", "Mumbai"], "Delhi"),
        ("Gateway of India kahan sthit hai?", ["Mumbai", "Delhi", "Kolkata", "Chennai"], "Mumbai"),
        ("Cricket team me kitne khiladi hote hain?", ["11", "9", "10", "12"], "11"),
        ("Hockey ka jadugar kise kehte hain?", ["Major Dhyan Chand", "Sachin Tendulkar", "Milkha Singh", "Kapil Dev"], "Major Dhyan Chand"),
        ("Olympic me kitne rings hote hain?", ["5", "4", "6", "7"], "5"),
        ("Chess me kul kitne squares (boxes) hote hain?", ["64", "32", "48", "80"], "64"),
        ("Suraj kis disha se ugta hai?", ["East", "West", "North", "South"], "East"),
        ("Paani ka chemical formula kya hai?", ["H2O", "CO2", "O2", "NaCl"], "H2O"),
        ("Manav sharir ka sabse bada ang (Organ) kaun sa hai?", ["Skin", "Heart", "Liver", "Brain"], "Skin"),
        ("Hawa me sabse zyada kaun si gas hoti hai?", ["Nitrogen", "Oxygen", "Carbon Dioxide", "Hydrogen"], "Nitrogen"),
        ("Bharat ka rashtriya pakshi (National Bird) kaun sa hai?", ["Mor (Peacock)", "Tota (Parrot)", "Kabootar (Pigeon)", "Cheel (Eagle)"], "Mor (Peacock)"),
        ("Bharat ka rashtriya pashu (National Animal) kaun sa hai?", ["Sher (Tiger)", "Sherni (Lion)", "Hathi (Elephant)", "Ghoda (Horse)"], "Sher (Tiger)"),
        ("Computer ka avishkar (Inventor) kise mana jata hai?", ["Charles Babbage", "Alan Turing", "Bill Gates", "Steve Jobs"], "Charles Babbage"),
        ("World War I kis varsh shuru hui thi?", ["1914", "1939", "1945", "1919"], "1914"),
        ("Solar System ka sabse bada grah (Planet) kaun sa hai?", ["Jupiter", "Saturn", "Mars", "Venus"], "Jupiter"),
    ]

    tier2_data = [
        ("Bharat ne purn swadhinta ka prastav kab paas kiya tha?", ["1929", "1947", "1930", "1942"], "1929"),
        ("Mahatma Gandhi ne Dandi March kab shuru kiya tha?", ["1930", "1920", "1942", "1919"], "1930"),
        ("Bharat ke pehle Pradhan Mantri kaun the?", ["Jawaharlal Nehru", "Sardar Patel", "Dr. Rajendra Prasad", "Mahatma Gandhi"], "Jawaharlal Nehru"),
        ("Mughal samrajya ki sthapna kisne ki thi?", ["Babur", "Akbar", "Humayun", "Aurangzeb"], "Babur"),
        ("Battle of Plassey kis varsh me hui thi?", ["1757", "1526", "1761", "1857"], "1757"),
        ("Manav sharir me kul kitni haddiyan hoti hain?", ["206", "208", "210", "195"], "206"),
        ("Vitamin C ki kami se kaun sa rog hota hai?", ["Scurvy", "Rickets", "Beriberi", "Night Blindness"], "Scurvy"),
        ("Paudhe kis prakriya se apna khana banate hain?", ["Photosynthesis", "Respiration", "Transpiration", "Digestion"], "Photosynthesis"),
        ("Blood ka pH maan lagbhag kitna hota hai?", ["7.4", "6.5", "8.0", "5.2"], "7.4"),
        ("Rakt (Blood) ka laal rang kiski wajah se hota hai?", ["Hemoglobin", "Plasma", "Platelets", "White Blood Cells"], "Hemoglobin"),
        ("Computer ka brain kise kehte hain?", ["CPU", "RAM", "Hard Disk", "Monitor"], "CPU"),
        ("HTML ka full form kya hai?", ["Hyper Text Markup Language", "High Tech Machine Language", "Hyperlink Text Mark Language", "Home Tool Markup Language"], "Hyper Text Markup Language"),
        ("Internet ka janak (Father of Internet) kise maana jata hai?", ["Vint Cerf", "Bill Gates", "Steve Jobs", "Tim Berners-Lee"], "Vint Cerf"),
        ("Python programming language kis varsh me launch hui thi?", ["1991", "1985", "1995", "2000"], "1991"),
        ("Keyboard kis prakar ka device hai?", ["Input", "Output", "Storage", "Processing"], "Input"),
        ("Bharat ka rashtriya gaan (National Anthem) kisne likha hai?", ["Rabindranath Tagore", "Bankim Chandra Chatterjee", "Muhammad Iqbal", "Subhash Chandra Bose"], "Rabindranath Tagore"),
        ("Lok Sabha ke sadasya ki nyuntam aayu (Minimum Age) kitni hoti hai?", ["25 Years", "21 Years", "30 Years", "35 Years"], "25 Years"),
        ("Rajya Sabha ke sadasya ka karyakal kitne varsh ka hota hai?", ["6 Years", "5 Years", "4 Years", "3 Years"], "6 Years"),
        ("Reserve Bank of India (RBI) ki sthapna kis varsh hui thi?", ["1935", "1947", "1950", "1920"], "1935"),
        ("Bitcoin kisne banaya tha?", ["Satoshi Nakamoto", "Vitalik Buterin", "Elon Musk", "Mark Zuckerberg"], "Satoshi Nakamoto"),
    ]

    tier3_data = [
        ("Light ki speed vacuum me kitni hoti hai?", ["300,000 km/s", "150,000 km/s", "3,000 km/s", "30,000 km/s"], "300,000 km/s"),
        ("Theory of Relativity kisne di thi?", ["Albert Einstein", "Isaac Newton", "Galileo Galilei", "Stephen Hawking"], "Albert Einstein"),
        ("Electron ki khoj kisne ki thi?", ["J.J. Thomson", "Ernest Rutherford", "James Chadwick", "Niels Bohr"], "J.J. Thomson"),
        ("Nuclear reactor me kaun sa element moderator ke roop me use hota hai?", ["Heavy Water (D2O)", "Graphite", "Uranium", "Boron"], "Heavy Water (D2O)"),
        ("Sound ki speed kis me sabse tez hoti hai?", ["Solid", "Liquid", "Gas", "Vacuum"], "Solid"),
        ("Bharat ka sanvidhan (Constitution) kab lagu hua tha?", ["26 January 1950", "15 August 1947", "26 November 1949", "2 October 1950"], "26 January 1950"),
        ("United Nations (UN) ki sthapna kis varsh hui thi?", ["1945", "1919", "1950", "1939"], "1945"),
        ("French Revolution kis varsh shuru hui thi?", ["1789", "1776", "1815", "1799"], "1789"),
        ("World War II ka ant kis varsh hua tha?", ["1945", "1942", "1950", "1939"], "1945"),
        ("Python me function banane ke liye kaun sa keyword use hota hai?", ["def", "func", "define", "lambda"], "def"),
        ("Python me kaun sa data type mutable (changeable) hota hai?", ["List", "Tuple", "String", "Int"], "List"),
        ("SQL ka full form kya hai?", ["Structured Query Language", "Simple Question Language", "Sequential Query Logic", "System Quality Language"], "Structured Query Language"),
        ("Artificial Intelligence (AI) ke pita (Father) kise kaha jata hai?", ["John McCarthy", "Alan Turing", "Geoffrey Hinton", "Yann LeCun"], "John McCarthy"),
        ("Inme se kaun si ek NoSQL database nahi hai?", ["MySQL", "MongoDB", "Cassandra", "Redis"], "MySQL"),
        ("Quantum Mechanics ke pita kise maana jata hai?", ["Max Planck", "Niels Bohr", "Albert Einstein", "Erwin Schrödinger"], "Max Planck"),
        ("DNA ka double helix model kisne diya تھا?", ["Watson and Crick", "Darwin and Wallace", "Mendel and Morgan", "Pasteur and Fleming"], "Watson and Crick"),
    ]

    for item in tier1_data:
        pool["tier_1"].append({"q": item[0], "options": item[1], "answer": item[2]})
    for item in tier2_data:
        pool["tier_2"].append({"q": item[0], "options": item[1], "answer": item[2]})
    for item in tier3_data:
        pool["tier_3"].append({"q": item[0], "options": item[1], "answer": item[2]})
        
    return pool

QUESTIONS_POOL = generate_questions()

def get_20_unique_questions(user_id, tier):
    session_data = user_sessions.get(user_id, {})
    used_set = session_data.get("used_questions", set())
    
    available_pool = [q for q in QUESTIONS_POOL[tier] if q["q"] not in used_set]
    
    if len(available_pool) < 20:
        used_set.clear()
        available_pool = QUESTIONS_POOL[tier].copy()
        
    selected = random.sample(available_pool, 20)
    for q in selected:
        used_set.add(q["q"])
        
    return selected, used_set

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    name = user.first_name

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    db_user = cursor.fetchone()

    if not db_user:
        cursor.execute("INSERT INTO users (user_id, name, wallet, verified) VALUES (?, ?, 100, 0)", (user_id, name))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        db_user = cursor.fetchone()

    conn.close()

    # Check verification status from DB
    if db_user["verified"] == 0:
        keyboard = [
            [InlineKeyboardButton("✅ I am 18+ & From Allowed State", callback_data="verify_yes")],
            [InlineKeyboardButton("❌ Under 18 / Banned State", callback_data="verify_no")]
        ]
        legal_disclaimer = (
            "⚖️ <b>LEGAL DISCLAIMER & AGE VERIFICATION</b> ⚖️\n\n"
            "Is paid skill-based game me enter karne se pehle kripya in niyamion ko dhyan se padhein:\n\n"
            "1️⃣ **Age Limit:** Aapki aayu kam se kam **18 varsh** honi chahiye.\n"
            "2️⃣ **Restricted States:** Agar aap **Assam, Odisha, Nagaland, Sikkim, Andhra Pradesh, ya Telangana** se hain, toh yeh game aapke liye prohibited hai.\n"
            "3️⃣ **Game of Skill:** Yeh pure knowledge-based game of skill hai.\n\n"
            "Kya aap upar di gayi sharton se sahamat hain?"
        )
        if update.message:
            await update.message.reply_text(legal_disclaimer, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.edit_message_text(legal_disclaimer, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    keyboard = [
        [InlineKeyboardButton("🟢 Tier 1 (Easy) • ₹10 | Target: 150", callback_data="tier_1")],
        [InlineKeyboardButton("🟡 Tier 2 (Medium) • ₹20 | Target: 165", callback_data="tier_2")],
        [InlineKeyboardButton("🔴 Tier 3 (Hard) • ₹50 | Target: 180", callback_data="tier_3")],
        [
            InlineKeyboardButton("💰 My Wallet", callback_data="check_wallet"), 
            InlineKeyboardButton("🏆 Leaderboard", callback_data="view_leaderboard")
        ],
        [InlineKeyboardButton("📜 Rules & Legal Terms", callback_data="view_rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        "╔═══════════════════════════╗\n"
        "✨      <b>QUIZ ARENA PRO</b>      ✨\n"
        "╚═══════════════════════════╝\n\n"
        f"👋 Welcome, <b>{name}</b>!\n\n"
        "🔥 <b>Game Features:</b>\n"
        "• 🧠 100% Non-Repeating Questions\n"
        "• ⏱️ 10s Live Single-Message Timer\n"
        "• ⚡ Paid Lifelines & 50% Exit Refund\n"
        "• 💰 Secure Database-Backed Payouts\n\n"
        "👇 <b>Select a Tier to Start Playing:</b>"
    )
    
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "📜 <b>TERMS, RULES & REGULATIONS</b> 📜\n\n"
        "1️⃣ **Eligibility:** Players must be 18+ years old and not reside in Assam, Odisha, Nagaland, Sikkim, Andhra Pradesh, or Telangana.\n"
        "2️⃣ **Entry Fee & Exit Policy:** Entry fee is deducted when starting a match. If you exit mid-game, **50% of the entry fee is automatically refunded** to your wallet.\n"
        "3️⃣ **Scoring & Penalties:** +10 points for correct answers, -3 points for incorrect answers or 10-second timeout.\n"
        "4️⃣ **Winning Payouts:** Meet the tier target score (Tier 1: 150, Tier 2: 165, Tier 3: 180) to instantly win **5x** your entry fee.\n"
        "5️⃣ **Fair Play:** Use of automated bots, multi-accounting, or cheating will result in a permanent ban and forfeiture of wallet funds."
    )
    keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
    if update.message:
        await update.message.reply_text(rules_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(rules_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT wallet, verified FROM users WHERE user_id = ?", (user_id,))
    db_user = cursor.fetchone()
    conn.close()

    if not db_user or db_user["verified"] == 0:
        await update.message.reply_text("⚠️ Pehle /start dabakar Age & Legal Verification complete karein.")
        return
        
    balance = db_user["wallet"]
    wallet_msg = (
        "╔═══════════════════════╗\n"
        "💰    <b>WALLET BALANCE</b>    💰\n"
        "╚═══════════════════════╝\n\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"💵 Available Balance: <b>₹{balance}</b>\n\n"
        "💡 <i>Play matches to win big rewards!</i>"
    )
    keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
    await update.message.reply_text(wallet_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT verified FROM users WHERE user_id = ?", (user_id,))
    db_user = cursor.fetchone()

    if not db_user or db_user["verified"] == 0:
        conn.close()
        await update.message.reply_text("⚠️ Pehle /start dabakar Age & Legal Verification complete karein.")
        return

    cursor.execute("SELECT name, score, tier FROM leaderboard ORDER BY score DESC LIMIT 10")
    top_players = cursor.fetchall()
    conn.close()

    if not top_players:
        msg = (
            "╔═══════════════════════╗\n"
            "🏆    <b>LEADERBOARD</b>     🏆\n"
            "╚═══════════════════════╝\n\n"
            "⚠️ Abhi tak koi high score record nahi hua hai.\n"
            "Match khelo aur top rank par aao!"
        )
    else:
        msg = (
            "╔═══════════════════════╗\n"
            "🏆  <b>TOP 10 LEADERBOARD</b>  🏆\n"
            "╚═══════════════════════╝\n\n"
        )
        for idx, row in enumerate(top_players, 1):
            medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"#{idx}"))
            msg += f"{medal} <b>{row['name']}</b>\n   └ Score: <code>{row['score']}</code> | [{row['tier'].upper()}]\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
    if update.message:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied!")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE verified = 1")
    verified_count = cursor.fetchone()["count"]
    cursor.execute("SELECT * FROM stats WHERE id = 1")
    stats = cursor.fetchone()
    conn.close()

    active_matches = len(user_sessions)
    stats_msg = (
        "🛠️ <b>ADMIN CONTROL DASHBOARD</b>\n\n"
        f"🎮 Active Matches: <code>{active_matches}</code>\n"
        f"👥 Total Verified Users: <code>{verified_count}</code>\n"
        f"💵 Total Entry Fees: <code>₹{stats['total_collected']}</code>\n"
        f"💸 Total Payouts: <code>₹{stats['total_payouts']}</code>\n"
        f"📈 Net House Earnings: <code>₹{stats['house_earnings']}</code>\n"
    )
    await update.message.reply_text(stats_msg, parse_mode="HTML")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    name = query.from_user.first_name

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    db_user = cursor.fetchone()

    if data == "verify_yes":
        cursor.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await start(update, context)
        return

    elif data == "verify_no":
        conn.close()
        await query.edit_message_text(
            text="⛔ <b>Access Denied</b>\n\nAapki aayu 18 se kam hai ya aap restricted state se hain, isliye aap is game me participate nahi kar sakte."
        )
        return

    if not db_user or db_user["verified"] == 0:
        conn.close()
        await start(update, context)
        return

    if data == "check_wallet":
        balance = db_user["wallet"]
        conn.close()
        wallet_msg = (
            "╔═══════════════════════╗\n"
            "💰    <b>WALLET BALANCE</b>    💰\n"
            "╚═══════════════════════╝\n\n"
            f"💵 Available Balance: <b>₹{balance}</b>"
        )
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(text=wallet_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "view_leaderboard":
        conn.clo
