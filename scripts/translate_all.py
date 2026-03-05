"""
ALL-IN-ONE translation: KR->EN TBL + CN->EN TBL + SQL desc_id + manual dict.
Applies to strings (file_00083), items (file_00084), spells (file_00085), and dialogue (file_00086).
"""
import re, os, zstandard, struct

TRANS = r"C:\Program Files (x86)\NCSOFT\Lineage Classic\translations"
OUT_DIR = os.path.join(os.environ['USERPROFILE'], 'lcx_final')
ORIG_DIR = os.path.join(os.environ['USERPROFILE'], 'lcx_decrypted')
SQL = os.path.join(TRANS, "l1jdb.sql")
dctx = zstandard.ZstdDecompressor()

def read_tbl(p, enc='utf-8-sig'):
    with open(p, 'r', encoding=enc, errors='replace') as f:
        return [l.rstrip('\r\n') for l in f.readlines()[1:]]

def compress_fit(mod_bytes, orig_path, out_path, label):
    with open(orig_path, 'rb') as f:
        orig = f.read()
    T_C = len(orig)
    T_D = len(dctx.decompress(orig, max_output_size=50*1024*1024))
    if len(mod_bytes) < T_D:
        mod_bytes += b' ' * (T_D - len(mod_bytes))
    elif len(mod_bytes) > T_D:
        mod_bytes = mod_bytes[:T_D]
    for lvl in [1, 3, 6, 10, 15, 19, 22]:
        cctx = zstandard.ZstdCompressor(level=lvl)
        c = cctx.compress(mod_bytes)
        if len(c) <= T_C:
            gap = T_C - len(c)
            if gap >= 8:
                padded = c + b'\x50\x2a\x4d\x18' + struct.pack('<I', gap-8) + b'\xAA' * (gap-8)
            elif gap > 0:
                padded = c + b'\xAA' * gap
            else:
                padded = c
            v = dctx.decompress(padded, max_output_size=50*1024*1024)
            assert len(v) == T_D
            with open(out_path, 'wb') as f:
                f.write(padded)
            print(f"  {label}: saved {len(padded)} bytes (lvl {lvl})")
            return True
    print(f"  {label}: ERROR cannot fit!")
    return False

# ============================================================
# BUILD ALL TRANSLATION SOURCES
# ============================================================
print("=== Building translation sources ===")

# 1) KR->EN from TBL (string translations)
kr_str = read_tbl(os.path.join(TRANS, "kr_string-k.tbl"), 'euc-kr')
en_str = read_tbl(os.path.join(TRANS, "kr_string-e.tbl"))
str_kr2en = {}
for i in range(min(len(kr_str), len(en_str))):
    k, e = kr_str[i].strip(), en_str[i].strip()
    if k and e and k != e:
        str_kr2en[k] = e

# KR->EN from TBL (desc/item translations)
kr_desc = read_tbl(os.path.join(TRANS, "kr_desc-k.tbl"), 'euc-kr')
en_desc = read_tbl(os.path.join(TRANS, "kr_desc-e.tbl"))
desc_kr2en = {}
for i in range(min(len(kr_desc), len(en_desc))):
    k, e = kr_desc[i].strip(), en_desc[i].strip()
    if k and e and k != e:
        desc_kr2en[k] = e

# 2) CN->EN
cn = read_tbl(os.path.join(TRANS, 'desc-c.tbl'))
en_old = read_tbl(os.path.join(TRANS, 'desc-e.tbl'))
cn2en = {}
for i in range(min(len(cn), len(en_old))):
    c, e = cn[i].strip(), en_old[i].strip()
    if c and e:
        cn2en[c] = e

# 3) SQL tables
sql_desc = {}
sql_npc = {}      # npc_id -> English name
sql_npc_name = {} # lowercase name -> English name
sql_skills = {}
sql_items_by_id = {}  # item_id -> English name
with open(SQL, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        if 'INSERT INTO' not in line:
            continue
        tm = re.search(r'INSERT INTO\s+`?(\w+)`?\s+VALUES', line)
        if not tm:
            continue
        table = tm.group(1)
        if table in ('armor', 'weapon', 'etcitem'):
            m = re.search(r"VALUES\s*\('(\d+)',\s*'([^']*)',\s*'([^']*)'", line)
            if m:
                item_id = int(m.group(1))
                name = m.group(2).replace('`', "'")
                sql_items_by_id[item_id] = name
                dm = re.search(r'\$(\d+)', m.group(3))
                if dm and name.strip():
                    sql_desc[int(dm.group(1))] = name
        elif table == 'npc':
            m = re.search(r"VALUES\s*\('(\d+)',\s*'([^']*)'", line)
            if m:
                npc_id = int(m.group(1))
                npc_name = m.group(2)
                sql_npc[npc_id] = npc_name
                sql_npc_name[npc_name.lower()] = npc_name
        elif table == 'skills':
            m = re.search(r"VALUES\s*\('(\d+)',\s*'([^']*)'", line)
            if m:
                sql_skills[int(m.group(1))] = m.group(2)

# 4) Manual dictionary (TW->EN) - comprehensive
manual = {
    # === Classes ===
    "王族":"Prince", "騎士":"Knight", "魔法師":"Wizard", "妖精":"Elf",
    "龍騎士":"Dragon Knight", "幻術士":"Illusionist", "戰士":"Warrior",
    # === Alignment ===
    "邪惡":"Chaotic", "中立":"Neutral", "正義":"Lawful",
    # === Stats ===
    "力量":"STR", "敏捷":"DEX", "體質":"CON", "智慧":"WIS", "智力":"INT", "魅力":"CHA",
    "經驗值":"EXP", "負重程度":"Weight", "飽食程度":"Food", "日/夜時間":"Time",
    "等級":"Level", "血量":"HP", "魔力值":"MP", "防禦力":"AC",
    "攻擊力":"Attack", "命中率":"Hit Rate", "迴避率":"Dodge Rate",
    "魔法防禦":"Magic Defense", "傷害減免":"Damage Reduction",
    "魔力":"MP", "體力":"HP",
    # === UI ===
    "確認":"OK", "取消":"Cancel", "設定":"Settings", "商店":"Shop",
    "是":"Yes", "否":"No", "關閉":"Close", "打開":"On", "返回":"Back",
    "儲存":"Save", "讀取":"Load", "刪除":"Delete", "確定":"Confirm",
    "離開":"Leave", "進入":"Enter", "接受":"Accept", "拒絕":"Reject",
    "開始":"Start", "結束":"End", "繼續":"Continue", "停止":"Stop",
    "交易":"Trade", "購買":"Buy", "販售":"Sell", "修理":"Repair",
    "裝備":"Equip", "使用":"Use", "丟棄":"Discard", "拾取":"Pick Up",
    "倉庫":"Warehouse", "存入":"Deposit", "取出":"Withdraw",
    "變身":"Polymorph", "解除":"Cancel", "傳送":"Teleport",
    "強化":"Enchant", "鑑定":"Identify", "對話":"Talk",
    "組隊":"Party", "血盟":"Clan", "公告":"Announcement",
    "挑戰":"Challenge", "決鬥":"Duel", "休息":"Rest",
    "頻道":"Channel", "伺服器":"Server",
    "成功":"Success", "失敗":"Failed",
    "小型":"Small", "中型":"Medium", "大型":"Large",
    "普通":"Normal", "特殊":"Special", "稀有":"Rare",
    "一般":"Normal", "魔法":"Magic", "祝福":"Blessed",
    "受詛咒的":"Cursed",
    "位置":"Position", "座標":"Coordinates",
    "前進":"Forward", "後退":"Back",
    "密語":"Whisper", "全體":"All", "隊伍":"Party",
    "友好":"Friendly", "敵對":"Hostile",
    # === NPC roles (CN) ===
    "妖魔族商人":"Orc Merchant", "倉庫管理員":"Warehouse Keeper",
    "雜貨商":"General Merchant", "執行者":"Host",
    "旅館老闆":"Innkeeper", "侍從長":"Head Attendant",
    "武器商":"Weapon Merchant", "防具商":"Armor Merchant",
    "村長":"Village Chief", "長老":"Elder", "門番":"Gatekeeper",
    "衛兵":"Guard", "騎士團長":"Knight Commander",
    "商人":"Merchant", "守衛":"Guard", "神官":"Priest",
    "國王":"King", "女王":"Queen", "王子":"Prince", "公主":"Princess",
    "衛兵隊長":"Guard Captain", "騎士團員":"Knight",
    "修道士":"Monk", "巫女":"Priestess", "占卜師":"Fortune Teller",
    "鐵匠":"Blacksmith", "寶石商":"Gem Trader", "藥水商":"Potion Dealer",
    "飾品商":"Accessory Merchant", "食品商":"Food Merchant", "船夫":"Boatman",
    "漁夫":"Fisherman", "獵人":"Hunter", "農夫":"Farmer",
    "傳送師":"Teleporter", "訓練師":"Trainer",
    "皮革商":"Leather Merchant", "布商":"Cloth Merchant",
    "食料品商":"Food Merchant", "魔法材料商":"Magic Supply Merchant",
    "交換員":"Exchange NPC", "門衛":"Gatekeeper",
    "傭兵隊長":"Mercenary Captain", "訓練官":"Training Master",
    "女巫":"Witch", "司祭":"Priest", "僧侶":"Monk",
    "寵物商":"Pet Merchant", "變身商":"Polymorph Merchant",
    "釣魚商":"Fishing Merchant",
    # === NPC proper names (CN->EN from SQL) ===
    "潘朵拉":"Pandora", "巴辛":"Basin", "朵琳":"Dorin", "露西":"Lucy",
    "凱倫":"Karen", "阿門":"Aman", "葛拉":"Gora", "梅格":"Mafu",
    "歐林":"Orim", "蓋爾":"Gale", "伊賽馬利":"Ishmael",
    "羅利雅":"Roria", "索拉雅":"Soraya", "巴歐":"Bahoff",
    "多瑪":"Doma", "沙罕阿吐巴":"Sagem Atuba", "索連":"Sram",
    "盧卡斯":"Lucas", "史提夫":"Steve", "史坦利":"Stanley",
    "保羅":"Paul", "菲利浦":"Phillip", "乃乃薛":"Nanashi",
    "赫乃":"Hector", "安東":"Anton", "貝莉莎":"Belissa",
    "米蘭達":"Miranda", "達金":"Tarkin", "乃瑞格":"Nereg",
    "寶金":"Bogin", "瑟蓮娜":"Selena", "高登":"Gordon",
    "凱特":"Kate", "伊利雅":"Ilia", "馬德":"Mard",
    # === Elements ===
    "火":"Fire", "水":"Water", "風":"Wind", "地":"Earth",
    # === Game items ===
    "斧":"Axe", "燈":"Lamp", "雙手劍":"Two-Handed Sword", "金幣":"Adena",
    "長劍":"Long Sword", "揮舞":"Wield", "無油":"No Oil",
    "精靈匕首":"Elven Dagger", "武士刀":"Katana",
    "釘錘":"Mace", "肉":"Meat", "弓":"Bow", "矛":"Spear",
    "治癒藥水":"Healing Potion", "楓木魔杖":"Maple Wand", "松木魔杖":"Pine Wand",
    "鑑定卷軸":"Identify Scroll", "漂浮之眼":"Floating Eye Meat",
    "卷軸":"Scroll", "藥水":"Potion", "戒指":"Ring", "項鍊":"Necklace",
    "頭盔":"Helm", "盔甲":"Armor", "盾牌":"Shield", "手套":"Gloves",
    "靴子":"Boots", "斗篷":"Cloak", "腰帶":"Belt", "耳環":"Earring",
    "弓箭":"Arrow", "魔杖":"Wand", "短劍":"Short Sword", "匕首":"Dagger",
    "木盾":"Wooden Shield", "鐵盾":"Iron Shield",
    "皮甲":"Leather Armor", "鏈甲":"Chain Mail", "鐵甲":"Plate Mail",
    "銀":"Silver", "金":"Gold", "鑽石":"Diamond",
    "強化卷軸":"Enchant Scroll", "回城卷軸":"Teleport Scroll",
    "復活卷軸":"Resurrection Scroll",
    "木劍":"Wooden Sword", "青銅劍":"Bronze Sword", "鐵劍":"Iron Sword",
    "銀劍":"Silver Sword", "雙手斧":"Two-Handed Axe",
    "紅色藥水":"Red Potion", "橘色藥水":"Orange Potion",
    "綠色藥水":"Green Potion", "勇敢藥水":"Brave Potion",
    "加速藥水":"Haste Potion", "魔力回復藥水":"Mana Recovery Potion",
    "恢復魔力":"Mana Recovery",
    "解毒劑":"Antidote", "萬能藥":"Elixir",
    "飛刀":"Throwing Knife", "手裏劍":"Shuriken",
    "箭矢":"Arrow", "銀箭":"Silver Arrow", "密銀箭":"Mithril Arrow",
    "食人妖精的血":"Ghoul Blood", "蛇毒":"Snake Venom",
    "狼皮":"Wolf Skin", "熊皮":"Bear Skin", "鹿皮":"Deer Skin",
    "寵物項圈":"Pet Collar",
    # === Monsters & NPCs ===
    "哥布林":"Goblin", "獸人":"Orc", "骷髏":"Skeleton", "殭屍":"Zombie",
    "蜘蛛":"Spider", "蛇":"Snake", "蝙蝠":"Bat", "老鼠":"Rat",
    "野狗":"Wild Dog", "狼":"Wolf", "熊":"Bear", "鹿":"Deer",
    "巨人":"Giant", "惡魔":"Demon", "龍":"Dragon", "精靈":"Elf/Spirit",
    "僵屍":"Zombie", "幽靈":"Ghost", "吸血鬼":"Vampire",
    "石像鬼":"Gargoyle", "地獄犬":"Hell Hound",
    "史萊姆":"Slime", "狼人":"Werewolf",
    "半獸人":"Orc", "食屍鬼":"Ghoul", "木乃伊":"Mummy",
    "暗黑精靈":"Dark Elf", "獸人戰士":"Orc Fighter",
    "獸人弓箭手":"Orc Archer", "地精":"Gnoll",
    "石頭巨人":"Stone Golem", "鉤爪惡魔":"Hook Horror",
    "土匪":"Bandit", "海盜":"Pirate", "小惡魔":"Imp",
    "牛頭怪":"Minotaur", "蠍子":"Scorpion", "甲蟲":"Beetle",
    # === Locations ===
    "說話之島":"Talking Island", "銀騎士村":"Silver Knight Town",
    "古魯丁":"Gludin", "風木村":"Windawood", "奇岩城":"Giran Castle",
    "海音城":"Heine", "亞丁":"Aden", "歐瑞":"Oren",
    "象牙塔":"Ivory Tower", "龍之谷":"Dragon Valley",
    "火焰之影城":"Fire Temple", "地底城":"Underground Castle",
    "肯特城":"Kent Castle", "妖魔城":"Orc Fortress",
    "威頓村":"Weden", "燃柳村":"Gludio",
    "妖精森林":"Elven Forest", "死亡騎士":"Death Knight",
    "荒島":"Deserted Island",
    # === System messages (full phrases) ===
    "攻城戰開始！":"Siege begins!", "攻城戰結束！":"Siege ended!",
    "已被佔領":"has been conquered", "攻城戰":"Siege War",
    "確定要":"Are you sure you want to",
    "請按下Quit結束遊戲。":"Please press Quit to exit the game.",
    "沒有任何事情發生。":"Nothing happened.",
    "你覺得舒服多了。":"You feel much better.",
    "不允許特殊文字或空格。":"Special characters or spaces are not allowed.",
    "該名稱已被使用。":"That name is already in use.",
    "創建角色成功。":"Character created successfully.",
    "無法使用該名稱。":"Cannot use that name.",
    "你的背包已滿。":"Your inventory is full.",
    "金幣不足。":"Not enough Adena.",
    "等級不足。":"Level too low.",
    "無法在此處使用。":"Cannot use here.",
    "你已經死亡。":"You have died.",
    "經驗值不足。":"Not enough EXP.",
    "該物品無法交易。":"This item cannot be traded.",
    "正在處理中...":"Processing...",
    "連線中斷。":"Connection lost.",
    "伺服器維護中。":"Server under maintenance.",
    "魔力不足。":"Not enough MP.",
    "體力不足。":"Not enough HP.",
    "請輸入角色名稱。":"Please enter a character name.",
    "你感到一股神秘的力量。":"You feel a mysterious force.",
    "請輸入密碼。":"Please enter a password.",
    "密碼錯誤。":"Wrong password.",
    "帳號已被鎖定。":"Account has been locked.",
    "請稍候再試。":"Please try again later.",
    "角色已被刪除。":"Character has been deleted.",
    "此功能暫時無法使用。":"This feature is temporarily unavailable.",
    "操作完成。":"Operation complete.",
    "你的寵物很開心。":"Your pet is happy.",
    "請選擇一個角色。":"Please select a character.",
    "目標太遠了。":"Target is too far.",
    "無法攻擊目標。":"Cannot attack target.",
    "你已經加入血盟。":"You have joined a clan.",
    "你已經離開血盟。":"You have left the clan.",
    "該血盟已滿員。":"That clan is full.",
    "對方拒絕了你的請求。":"The other party rejected your request.",
    "交易完成。":"Trade completed.",
    "交易已取消。":"Trade cancelled.",
    "你已經裝備了此物品。":"You have equipped this item.",
    "你無法裝備此物品。":"You cannot equip this item.",
    "物品已強化。":"Item has been enchanted.",
    "強化失敗。":"Enchantment failed.",
    "準備完成":"Ready",
    "移動中":"Moving",
    "戰鬥中":"In Combat",
    "休息中":"Resting",
    "施法中":"Casting",
    "死亡":"Dead",
    "線上":"Online", "離線":"Offline",
    "選擇":"Select", "確認刪除":"Confirm Delete",
    "已過期":"Expired", "已完成":"Completed",
    "排行":"Ranking", "排名":"Rank",
    "魔法帳":"Magic Tent", "帳號":"Account",
    "中斷":"Disconnect", "封鎖":"Block",
    "戰鬥模式":"Combat Mode", "和平模式":"Peace Mode",
    "攻擊模式":"Attack Mode",
    "全體頻道":"All Channel",
    "隊伍頻道":"Party Channel",
    "血盟頻道":"Clan Channel",
    "交易頻道":"Trade Channel",
    "密語頻道":"Whisper Channel",
    # === Template strings (auto-translated) ===
    "\f3伺服器將會在{}秒後關機。請玩家先行離線。":"\f3Server will shut down in {} seconds. Please log off now.",
    "{0}%s離開了{1}血盟。":"Clan: {0}%s has left {1} clan.",
    "{}%d 不在線上。":"{}%d is not online.",
    "{}%d 不是血盟的盟主。":"{}%d is not the clan leader.",
    "{}%d 尚未創立血盟。":"{}%d has not created a clan.",
    "{}%d的血盟已經一員而無法加入更多的人了。":"{}%d's clan is full and cannot accept more members.",
    "{}%d還不是你血盟的成員,必須先接受對方當你的血盟成員。":"{}%d is not yet a clan member. You must first accept them.",
    "{}%d金幣。":"{}%d Adena.",
    "{}%o 已被強化。":"{}%o has been enchanted.",
    "{}%o已損壞。":"{}%o has been damaged.",
    "{}%s 向你要求交易。":"{}%s requests to trade with you.",
    "{}%s 向你要求加入血盟,你願意嗎?(Y/N)":"{}%s wants to join your clan. Do you accept? (Y/N)",
    "{}%s 已離開你的血盟。":"{}%s has left your clan.",
    "{}%s 正在攻擊你。":"{}%s is attacking you.",
    "{}%s 沒有面對看你。":"{}%s is not facing you.",
    "{}%s 被逐出你的血盟。":"{}%s has been expelled from your clan.",
    "{}%s向你挑戰決鬥。(Y/N)":"{}%s challenges you to a duel. (Y/N)",
    "{}%s已加入隊伍。":"{}%s has joined the party.",
    "{}%s已拒絕你的決鬥。":"{}%s rejected your duel.",
    "{}%s已接受你的決鬥。":"{}%s accepted your duel.",
    "{}%s已離開隊伍。":"{}%s has left the party.",
    "{}%s要求和你組隊,你願意嗎?(Y/N)":"{}%s wants to form a party with you. (Y/N)",
    "{}已死亡。":"{} has died.",
    "{}的{}已經破碎了。":"{}'s {} has broken.",
    "一般道具":"Normal Item",
    "下載中":"Downloading",
    "不同意":"Disagree",
    "不是":"No",
    "不行":"No",
    "中斷連線":"Disconnecting",
    "任務":"Quest",
    "任務道具":"Quest Item",
    "你向{}%s提出決鬥。":"You challenged {}%s to a duel.",
    "你已攻擊{}%o。":"You attacked {}%o.",
    "你已被{}攻擊。":"You have been attacked by {}.",
    "你接受{}%o當你的血盟成員。":"You accepted {}%o as your clan member.",
    "你殺了{}%o。":"You killed {}%o.",
    "你無法攜帶更多的{}。":"You cannot carry more {}.",
    "你的寵物{}已死亡。":"Your pet {} has died.",
    "你的寵物{}已餓了。":"Your pet {} is hungry.",
    "你選擇了{}。":"You selected {}.",
    "傳送":"Teleport",
    "傳送至{}。":"Teleported to {}.",
    "價格":"Price",
    "全部":"All",
    "公告欄":"Bulletin Board",
    "剩餘":"Remaining",
    "創立{}血盟。":"Created {} clan.",
    "加入{}血盟。":"Joined {} clan.",
    "升級":"Level Up",
    "卸下{}%o。":"Unequipped {}%o.",
    "取消退出":"Cancel Exit",
    "召喚":"Summon",
    "吃了{}%o。":"Ate {}%o.",
    "同伴":"Companion",
    "同意":"Agree",
    "命中":"Hit",
    "回避":"Dodge",
    "在{}中找到了。":"Found in {}.",
    "地圖":"Map",
    "失去了{}%o。":"Lost {}%o.",
    "女性":"Female",
    "好友名單":"Friends List",
    "好的":"OK",
    "存檔中":"Saving",
    "安裝中":"Installing",
    "寵物名稱已變更為{}。":"Pet name changed to {}.",
    "屬性抗性":"Elemental Resistance",
    "已丟棄{}%o。":"Discarded {}%o.",
    "已使用{}的治療。":"Used {}'s healing.",
    "已修理":"Repaired",
    "已售出":"Sold",
    "已將物品存入{}。":"Deposited items in {}.",
    "已強化":"Enchanted",
    "已從{}取出物品。":"Withdrew items from {}.",
    "已從{}購買了商品。":"Purchased items from {}.",
    "已拾取{}%o。":"Picked up {}%o.",
    "已施展{}。":"Cast {}.",
    "已裝備{}%o。":"Equipped {}%o.",
    "已購買":"Purchased",
    "已過期的":"Expired",
    "帳號登入":"Account Login",
    "建立帳號":"Create Account",
    "強化":"Enchant",
    "得到了{}%o。":"Obtained {}%o.",
    "從{}%s接收金幣。":"Received Adena from {}%s.",
    "復活":"Resurrection",
    "忽略名單":"Ignore List",
    "怪物":"Monster",
    "戰鬥力":"Combat Power",
    "技能欄":"Skills",
    "持有金額":"Adena",
    "攻擊速度":"Attack Speed",
    "敵人":"Enemy",
    "數量":"Quantity",
    "數量不足{}%o。":"Insufficient amount of {}%o.",
    "施法速度":"Cast Speed",
    "是的":"Yes",
    "暴擊":"Critical",
    "暴擊率":"Critical Rate",
    "更新中":"Updating",
    "最大HP":"Max HP",
    "最大MP":"Max MP",
    "材料":"Material",
    "正在連線...":"Connecting...",
    "武器等級":"Weapon Level",
    "治療":"Heal",
    "消耗品":"Consumable",
    "無":"None",
    "無效的":"Invalid",
    "無法使用{}%o。":"Cannot use {}%o.",
    "物品等級":"Item Level",
    "特殊能力":"Special Ability",
    "獲得了{}經驗值。":"Gained {} experience points.",
    "玩家":"Player",
    "現在位置":"Current Location",
    "男性":"Male",
    "當前HP":"Current HP",
    "當前MP":"Current MP",
    "目前{}等金幣。":"Currently {} Adena.",
    "目標":"Target",
    "確認密碼":"Confirm Password",
    "確認退出":"Confirm Exit",
    "祝福":"Bless",
    "移動速度":"Move Speed",
    "稀有道具":"Rare Item",
    "稍等片刻":"Please wait a moment",
    "種族":"Race",
    "等級提升!目前{}等級。":"Level Up! You are now level {}.",
    "系統訊息":"System Message",
    "經驗值":"Experience",
    "總計":"Total",
    "耐久度":"Durability",
    "聊天":"Chat",
    "職業":"Class",
    "背包":"Inventory",
    "自動攻擊":"Auto Attack",
    "自己":"Self",
    "裝備品":"Equipment",
    "裝備欄":"Equipment",
    "角色刪除":"Delete Character",
    "角色創建":"Character Creation",
    "角色資訊":"Character Info",
    "角色選擇":"Character Select",
    "解毒":"Cure Poison",
    "詛咒":"Curse",
    "請等待":"Please wait",
    "變身":"Polymorph",
    "負重":"Weight",
    "費用":"Cost",
    "載入中":"Loading",
    "輸入密碼":"Enter Password",
    "近戰攻擊":"Melee Attack",
    "近距離攻擊":"Melee Attack",
    "遊戲內容":"Game Content",
    "遊戲時間":"Game Time",
    "遊戲設定":"Game Settings",
    "道具使用":"Item Use",
    "遠程攻擊":"Ranged Attack",
    "遠距攻擊":"Ranged Attack",
    "選擇伺服器":"Select Server",
    "重量":"Weight",
    "金幣數量":"Adena Amount",
    "鑑定":"Identify",
    "防具等級":"Armor Level",
    "魔法值":"MP",
    "魔法抗性":"Magic Resistance",
    "魔法攻擊":"Magic Attack",
    "魔法等級":"Magic Level",
    "黑名單":"Block List",
    # === Buff timer / Arena announcements (items 1612-1615) ===
    "離比賽開始":"Time Remaining",
    "分後比賽將開始。":"min. until starting.",
    "分鐘後比賽將開始，想參賽者請現在入場。":"min. until starting. Participants please enter now.",
    "現在怪物即將登場。祝你好運！！":"Monsters will appear now. Good luck!!",
    "剩餘時間":"Time Remaining",
    "剩餘時間：":"Time Remaining:",
    # === Auto-translated items (KR substring + CN component matching) ===
    "%i的獵人之弓":"Hunter Bow",
    "%i的骷髏盔甲":"%i的 Bone Armor",
    "%i的骷髏盾牌":"%i的 Bone Shield",
    "%i的骷髏頭盔":"%i的 Skull Helmet",
    "(魂體轉換)":"(Bloody Soul)",
    "2色(白紅)花粉":"Red and White",
    "2色(紅黃)花粉":"Red and Yellow",
    "2色(黃藍)花粉":"Yellow and Blue",
    "GM隱身斗篷":"Cloak of Invisibility",
    "[古魯丁村]":"Gludin Town",
    "[奇岩村]":"Giran Castle Town",
    "[燃柳村]":"Fire-Field Farmers Town",
    "[銀騎士村]":"Silver Knight Town",
    "[風木村]":"Woodbeck Village",
    "丙午年變形卷軸":"Polymorph Scroll",
    "事前預約禮物箱":"Gift Chest",
    "亞修2段加速袋":"Acceleration Pouch",
    "侍從長^沙罕阿吐巴":"Head Attendant^Sagem Atuba",
    "倉庫管理員":"Storage^Garin",
    "倉庫管理員^克哈丁":"Storage^Kuhatin",
    "倉庫管理員^塔奇":"Storage^Tarkin",
    "倉庫管理員^奧克倫":"Storage^Orclon",
    "倉庫管理員^巴歐":"Storage^Bahof",
    "倉庫管理員^托芬":"Storage^Tofen",
    "倉庫管理員^朵琳":"Storage^Doreen",
    "倉庫管理員^索連":"Storage^Thram",
    "倉庫管理員^蘇瑞耳":"Storage^Sauram",
    "倉庫管理員^諾丁":"Storage^Nodim",
    "倉庫管理員^高特":"Storage^Gotham",
    "出現了首領。":"The Doppelganger boss has appeared.",
    "剩餘時間":"Until the start of the competition",
    "史萊姆競賽":"Slime Race Track",
    "呼喚盟友":"(Call Pledge Member)",
    "和平神女^瑟琳娜":"和平神女^Selena",
    "地下通道":"Enter the Hunting Grounds",
    "地獄的妖魔巡守":"Orc Scout",
    "地獄的安普長老":"Imp Elder",
    "地獄的思克巴女皇":"Succubus Queen",
    "地獄的死亡騎士":"Death Knight",
    "地獄的邪惡蜥蜴":"Wandering Dark Guard",
    "地獄的骷髏神射手":"地獄的 Skeleton Marksman",
    "執行者^梅格":"Host^Mafu",
    "執行者^葛拉":"Host^Gora",
    "執行者^阿門":"Host^Aman",
    "墮落的光精靈王":"Great Spirit of Light",
    "墮落的地精靈王":"Earth Spirit",
    "墮落的妖魔弓箭手":"Orc Archer",
    "墮落的妖魔法師":"Orc Wizard",
    "墮落的妖魔鬥士":"Orc Fighter",
    "墮落的曼陀羅草":"Mandragora",
    "墮落的樹精召喚物":"Servant of Spirit",
    "墮落的水精靈王":"Water Spirit",
    "墮落的甘地妖魔":"Gandi Orc",
    "墮落的都達瑪拉妖魔":"Duda-Mara Orc",
    "墮落的闇精靈王":"Dark Spirit",
    "墮落的風精靈王":"Wind Spirit",
    "奇岩城":"Giran Castle Town",
    "套裝加成":"[Set Bonus]",
    "寵物商人":"Pet Merchant^Killington",
    "寵物管理人":"Pet Keeper^Rick",
    "寵物道具製作":"Pet Item Crafter^Nose",
    "寵物雜貨商人":"Pet Merchant^Dick",
    "布料商人^愛弗特":"布料商人^Evert",
    "幸運的信":"Psy's Lucky Letter",
    "強化自我加速藥水":"Haste Potion",
    "往說話之島的船":"Talking Island Boat Ticket",
    "恢復神女":"Priestess of Recovery^Agatha",
    "情書":"Crumpled Up Breaking-Up Letter",
    "新手便利":"Beginner's Helper^Guide",
    "旅館會議廳鑰匙(古魯丁村)":"Gludin Town",
    "旅館會議廳鑰匙(奇岩村)":"Giran Castle Town",
    "旅館會議廳鑰匙(說話之島村)":"Talking Island Village",
    "旅館會議廳鑰匙(銀騎士村)":"Silver Knight Town",
    "旅館會議廳鑰匙(風木村)":"Woodbeck Village",
    "旅館鑰匙(古魯丁村)":"Gludin Town",
    "旅館鑰匙(奇岩村)":"Inn Room Key",
    "旅館鑰匙(說話之島村)":"Talking Island Village",
    "旅館鑰匙(銀騎士村)":"Silver Knight Town",
    "旅館鑰匙(風木村)":"Woodbeck Village",
    "武器商人":"Merchant^Werner",
    "武器防具商人":"Weapon Merchant^Balsim",
    "污染的光精靈王":"Great Spirit of Light",
    "污染的妖魔斧兵":"Contaminated Orc",
    "污染的妖魔槍兵":"Contaminated Orc",
    "污染的水精靈":"Contaminated Spirit Stone of Water",
    "污染的火精靈":"Contaminated Spirit Stone of Fire",
    "沙哈的項鍊":"Saiha's Amulet",
    "沙漠綠洲":"Desert Oasis",
    "漂浮之眼肉":"Floating Eye 肉",
    "無界擂台":"Colosseum Caretaker",
    "燃柳村傳送師":"Fire Field Teleporter^Cobb",
    "獎勵管理":"Reward Keeper^Donju",
    "皮革加工師":"Leathersmith^Julie",
    "皮革商人^菲力浦":"皮革商人^Philip",
    "第 ":"Furniture Merchant^Jack",
    "精靈魔法":"Aden's Spirit Magic Box",
    "精靈魔法傳授者":"Spirit Elemental^Ellyonne",
    "精靈魔法商^琳達":"精靈魔法商^Linda",
    "紅色藥水袋":"Lesser Healing Potion",
    "綠洲":"Desert Oasis",
    "老舊的精神腰帶":"Belt of Mind",
    "老舊的身體皮帶":"Belt of Body",
    "老舊的靈魂皮帶":"Belt of Soul",
    "肯特村":"Hit List (Kent)",
    "藥水商人":"Merchant^Randal",
    "血盟執行人":"Clan Manager^Blood Clan",
    "裁縫師^哈巴特":"裁縫師^Herbert",
    "說話之島地監1樓":"Talking Island Dungeon",
    "說話之島地監1樓(網咖)":"Talking Island Dungeon",
    "說話之島地監2樓":"Talking Island Dungeon",
    "說話之島地監2樓(網咖)":"Talking Island Dungeon",
    "說話之島港口":"Templar Trainer^Doaman",
    "說話的卷軸(妖精)":"Talking Scroll",
    "說話的卷軸(王族)":"Talking Scroll",
    "說話的卷軸(騎士)":"Talking Scroll",
    "說話的卷軸(魔法師)":"Talking Scroll",
    "變種巨蟻地監":"Giant Ant",
    "輕量勇敢藥水":"Brave Potion",
    "輕量對武器施法的卷軸":"Scroll of Enchant Weapon",
    "輕量對盔甲施法的卷軸":"Scroll of Enchant Armor",
    "輕量惡魔之血":"Devil Blood",
    "輕量慎重藥水":"Wisdom Potion",
    "輕量瞬間移動卷軸":"輕量 Scroll of Teleportation",
    "輕量精靈餅乾":"Elven Wafer",
    "輕量紅色藥水":"Lesser Healing Potion",
    "輕量自我加速藥水":"Haste Potion",
    "輕量藍色藥水":"Mana Potion",
    "輕量變形卷軸":"Polymorph Scroll",
    "輕量返回卷軸":"Escape Scroll",
    "迎春節^林果":"迎春節^Lengo",
    "道具製作":"Item Crafter^Pin",
    "閃耀的2段加速袋":"Acceleration Pouch",
    "防具商人":"Weapon Merchant^Balsim",
    "防具商人^范吉爾":"Merchant^Vergil",
    "雜貨商人":"General Merchant^Serine",
    "風木內城":"Windawood Inner Castle",
    "風木城北邊獵場":"Windawood Castle",
    "風木城地監":"Windawood Castle",
    "風木城地監1樓":"Windawood Castle",
    "風木城地監2樓":"Windawood Castle",
    "風木城警衛":"Windawood Castle",
    "食材商人":"Grocery Shop^Sharu",
    "骨頭加工師":"Bone Crafter^Joel",
    "魔力回復藥水":"Els Magic Recovery Potion",
    "魔法傳授者":"Elven Magician^Horun",
    "魔法煉金術師":"Magic Alchemist^Moria",
    "龍之谷入口":"Dragon Valley",
    "龍之谷地監1樓":"Dragon Valley",
    "龍之谷地監2樓":"Dragon Valley",
    "龍之谷地監3樓":"Dragon Valley",
    "龍之谷地監4樓":"Dragon Valley",
    "龍之谷地監5樓":"Dragon Valley",
    "龍之谷地監6樓":"Dragon Valley",
    "龍之谷地監7樓":"Dragon Valley",
    "龍之谷地監入口":"Dragon Valley",
    "龍之谷黑長者出沒地區":"Dragon Valley",
}

# 4b) Korean NPC role dictionary for compound name splitting
kr_roles = {
    "창고지기": "Warehouse Keeper", "여관대여": "Innkeeper", "텔레포터": "Teleporter",
    "잡화상": "General Merchant", "옷감 상인": "Cloth Merchant", "가죽 상인": "Leather Merchant",
    "대장장이": "Blacksmith", "진행자": "Host", "시종장": "Head Attendant",
    "무기 상인": "Weapon Merchant", "방어구 상인": "Armor Merchant", "마을 이장": "Village Chief",
    "마법 재료 상인": "Magic Supply Merchant", "식료품 상인": "Food Merchant",
    "오크족 상인": "Orc Merchant", "약수 상인": "Potion Merchant",
    "장신구 상인": "Accessory Merchant", "보석 세공사": "Jeweler",
    "교환원": "Exchange NPC", "경비병": "Guard", "문지기": "Gatekeeper",
    "기사단장": "Knight Commander", "용병대장": "Mercenary Captain",
    "훈련관": "Training Master", "사냥꾼": "Hunter", "어부": "Fisherman",
    "선원": "Sailor", "마녀": "Witch", "사제": "Priest", "수도사": "Monk",
    "장로": "Elder", "경기 시작": "Game Start",
}

# 4c) CN word-component dictionary for item name translation
# Sorted longest-first when used, for greedy matching
cn_item_dict = {
    # Weapon types
    "雙手劍": "Two-Handed Sword", "雙手斧": "Two-Handed Axe",
    "長劍": "Long Sword", "短劍": "Short Sword", "闊劍": "Broadsword",
    "彎刀": "Scimitar", "匕首": "Dagger", "武士刀": "Katana",
    "細劍": "Rapier", "木劍": "Wooden Sword",
    "長弓": "Long Bow", "短弓": "Short Bow", "十字弓": "Crossbow",
    "長槍": "Lance", "三叉戟": "Trident", "短槍": "Short Spear",
    "權杖": "Scepter", "法杖": "Staff", "魔杖": "Wand",
    "戰槌": "War Hammer", "鏈鎚": "Flail", "釘錘": "Mace",
    "手裏劍": "Shuriken", "飛刀": "Throwing Knife",
    # Armor types
    "板金鎧甲": "Plate Mail", "鎖鏈甲": "Chain Mail",
    "鱗甲": "Scale Mail", "皮甲": "Leather Armor",
    "全身鎧甲": "Full Plate", "長袍": "Robe",
    "鎧甲": "Armor", "盔甲": "Armor",
    # Armor pieces
    "板金頭盔": "Plate Helm", "全盔": "Full Helm",
    "皮盔": "Leather Helm", "鐵盔": "Iron Helm",
    "頭盔": "Helm",
    "板金盾": "Plate Shield", "塔盾": "Tower Shield",
    "圓盾": "Round Shield", "銀盾": "Silver Shield",
    "木盾": "Wooden Shield", "鐵盾": "Iron Shield",
    "盾牌": "Shield",
    "板金手套": "Plate Gloves", "銀手套": "Silver Gloves",
    "鐵手套": "Iron Gloves", "皮手套": "Leather Gloves",
    "金屬手套": "Metal Gloves", "手套": "Gloves",
    "鐵靴": "Iron Boots", "皮靴": "Leather Boots",
    "鋼鐵靴": "Steel Boots", "長靴": "Long Boots",
    "靴子": "Boots",
    "斗篷": "Cloak", "披風": "Cape",
    "腰帶": "Belt",
    # Accessories
    "護身符": "Amulet", "手鐲": "Bracelet", "胸針": "Brooch",
    "墜飾": "Pendant", "寶珠": "Orb",
    "戒指": "Ring", "項鍊": "Necklace", "耳環": "Earring",
    # Materials/qualities
    "密銀": "Mithril", "鋼鐵": "Steel", "青銅": "Bronze",
    "黃金": "Golden", "白金": "Platinum", "水晶": "Crystal",
    "黑曜石": "Obsidian", "紅寶石": "Ruby", "藍寶石": "Sapphire",
    "綠寶石": "Emerald", "紫水晶": "Amethyst",
    "碧玉": "Jade", "皮革": "Leather", "絲綢": "Silk",
    # Prefixes
    "魔法師的": "Wizard's", "騎士的": "Knight's",
    "精靈的": "Elven", "龍騎士的": "Dragon Knight's",
    "王族的": "Royal", "戰士的": "Warrior's",
    "古代的": "Ancient", "傳說的": "Legendary",
    "暗黑的": "Dark", "神聖的": "Holy",
    "閃耀的": "Shining", "光輝的": "Radiant",
    # Consumables
    "治癒藥水": "Healing Potion", "加速藥水": "Haste Potion",
    "魔力回復藥水": "Mana Recovery Potion",
    "紅色藥水": "Red Potion", "橘色藥水": "Orange Potion",
    "綠色藥水": "Green Potion", "藥水": "Potion",
    "解毒劑": "Antidote", "萬能藥": "Elixir",
    # Scrolls
    "強化卷軸": "Enchant Scroll", "鑑定卷軸": "Identify Scroll",
    "回城卷軸": "Teleport Scroll", "復活卷軸": "Resurrection Scroll",
    "卷軸": "Scroll",
    # Other items
    "箭矢": "Arrow", "銀箭": "Silver Arrow", "密銀箭": "Mithril Arrow",
    "寵物項圈": "Pet Collar", "結婚戒指": "Wedding Ring",
    "釣竿": "Fishing Rod", "魚餌": "Bait",
    "鑰匙": "Key", "寶箱": "Chest",
    "火把": "Torch", "燈": "Lamp",
    # Connector words
    "之": " of ", "的": "'s ",
}
_cn_item_sorted = sorted(cn_item_dict.items(), key=lambda x: -len(x[0]))

def translate_cn_item(text):
    """Try to translate a Chinese item name using word components."""
    result = text
    for cn_word, en_word in _cn_item_sorted:
        result = result.replace(cn_word, en_word)
    # Clean up
    result = re.sub(r'\s+', ' ', result).strip()
    # Check if fully translated (no remaining CJK)
    remaining_cn = sum(1 for c in result if '\u4e00' <= c <= '\u9fff')
    if remaining_cn == 0:
        return result
    return None  # Not fully translated


def lookup(kr, tw, rid=0):
    """Try all sources to find English translation."""
    # Exact manual TW match (highest priority)
    if tw in manual:
        return manual[tw]
    # CN/TW match (before KR desc - KR desc TBL has bad entries 35749-35758)
    if tw in cn2en:
        return cn2en[tw]
    # SQL desc_id
    if rid and rid in sql_desc:
        return sql_desc[rid]
    # KR match in string TBL (generally reliable)
    if kr in str_kr2en:
        return str_kr2en[kr]
    # KR match in desc TBL (has some bad mappings, checked last)
    if kr in desc_kr2en:
        return desc_kr2en[kr]
    # Try compound names with ^
    if '^' in tw or '^' in kr:
        # Try TW compound first
        if '^' in tw:
            tw_parts = tw.split('^')
            en_parts = []
            any_translated = False
            for p in tw_parts:
                ep = manual.get(p) or cn2en.get(p)
                if ep:
                    en_parts.append(ep)
                    any_translated = True
                else:
                    en_parts.append(p)
            if any_translated:
                return '^'.join(en_parts)
        # Try KR compound
        if '^' in kr:
            kr_parts = kr.split('^')
            en_parts = []
            any_translated = False
            for kp in kr_parts:
                # Check KR role dict
                if kp in kr_roles:
                    en_parts.append(kr_roles[kp])
                    any_translated = True
                # Check SQL NPC names
                elif kp.lower() in sql_npc_name:
                    en_parts.append(sql_npc_name[kp.lower()])
                    any_translated = True
                # Check KR->EN TBLs
                elif kp in str_kr2en:
                    en_parts.append(str_kr2en[kp])
                    any_translated = True
                elif kp in desc_kr2en:
                    en_parts.append(desc_kr2en[kp])
                    any_translated = True
                else:
                    en_parts.append(kp)
            if any_translated:
                return '^'.join(en_parts)
    return None

# 5) Spell data (same as before)
spell_name_map = {
    "LesserHeal": "Lesser Heal", "Light": "Light", "Shield": "Shield",
    "EBolt": "Energy Bolt", "Teleport": "Teleport", "IceDagger": "Ice Dagger",
    "WindShuriken": "Wind Cutter", "HolyWeapon": "Holy Weapon",
    "CurePoison": "Cure Poison", "ChillTouch": "Chill Touch",
    "Poison": "Curse: Poison", "EnchantWeapon": "Enchant Weapon",
    "Detection": "Detection", "DecreaseWeight": "Decrease Weight",
    "FireArrow": "Fire Arrow", "Stalac": "Stalac", "Lightning": "Lightning",
    "TurnUndead": "Turn Undead", "Heal": "Heal", "Blind": "Blind",
    "WeaponBreak": "Weapon Break", "VampiricTouch": "Vampiric Touch",
    "SlowCloud": "Slow Cloud", "Curse": "Curse", "MedusaEye": "Medusa Eye",
    "CounterBarrier": "Counter Barrier", "Haste": "Haste",
    "CreateZombie": "Create Zombie", "GreaterHeal": "Greater Heal",
    "DarkBlind": "Dark Blind", "WeakenMagic": "Weaken Magic",
    "PoisonCloud": "Poison Cloud", "CancelMagic": "Cancel Magic",
    "EarthJail": "Earth Jail", "SummonMonster": "Summon Monster",
    "HolyWalk": "Holy Walk", "Tornado": "Tornado",
    "GrandBishopHealing": "Grand Bishop Healing",
    "CallLightning": "Call Lightning", "Fireball": "Fireball",
    "IceStorm": "Ice Storm", "CounterMirror": "Counter Mirror",
    "CharmedMonster": "Charm Monster", "WrathOfEvil": "Wrath of Evil",
    "EruDivineProtection": "Eru's Divine Protection",
    "ValaraDivineProtection": "Valara's Divine Protection",
    "CounterDetection": "Counter Detection",
    "CreateHigherUndead": "Create Higher Undead",
    "Resurrection": "Resurrection", "MagicBooster": "Magic Booster",
    "BlessWeapon": "Bless Weapon", "AbsoluteBarrier": "Absolute Barrier",
    "AdvancedSpiritBlast": "Advanced Spirit Blast",
    "BodyToMind": "Body to Mind", "TelToMother": "Teleport to Mother",
    "TrueTarget": "True Target", "CallOfNature": "Call of Nature",
    "TripleArrow": "Triple Arrow", "Concentrate": "Concentrate",
    "ShadowFang": "Shadow Fang", "DoubleBreak": "Double Break",
    "NaturesMiracle": "Nature's Miracle", "ReturnToNature": "Return to Nature",
    "WindWalk": "Wind Walk", "PolymorphDrake": "Polymorph: Drake",
    "PolymorphWolf": "Polymorph: Wolf", "PolymorphBear": "Polymorph: Bear",
    "PolymorphOgre": "Polymorph: Ogre",
    "Uncanny": "Uncanny Dodge", "FoeSlayer": "Foe Slayer",
    "Mortal": "Mortal Body", "Berserker": "Berserker",
    "ShockStun": "Shock Stun", "IronSkin": "Iron Skin",
    "ReduceWeight": "Reduce Weight", "SoulOfFlame": "Soul of Flame",
    "DragonSkin": "Dragon Skin", "BurningSlash": "Burning Slash",
    "GuardBreak": "Guard Break", "MagmaBreath": "Magma Breath",
    "AwakeningOre": "Awakening Ore",
    "IllusionOgre": "Illusion: Ogre", "IllusionLich": "Illusion: Lich",
    "IllusionDiaGolem": "Illusion: Diamond Golem",
    "IllusionAvatar": "Illusion: Avatar",
    "PatienceAura": "Patience Aura", "CounterMagic": "Counter Magic",
    "MirrorImage": "Mirror Image", "Confusion": "Confusion",
    "Smash": "Smash", "IllusionDKnights": "Illusion: Death Knight",
    "InsightAura": "Insight Aura", "PanicAura": "Panic Aura",
    "PhysicalEnchantDex": "Physical Enchant: DEX",
    "PhysicalEnchantStr": "Physical Enchant: STR",
    "FireWeapon": "Fire Weapon", "WindShot": "Wind Shot",
    "IronSkinScroll": "Iron Skin", "EarthBind": "Earth Bind",
    "BoneBreak": "Bone Break", "NaturesBless": "Nature's Blessing",
    "Entangle": "Entangle",
    "ManaRecovery": "Mana Recovery", "Silence": "Silence",
    "Darkness": "Darkness",
}

spell_desc_kr = {
    "종류": "Type", "성향": "Alignment", "재료": "Cost",
    "지속시간": "Duration", "대상": "Target",
    "치료": "Healing", "공격": "Attack", "보조": "Support",
    "바람": "Wind", "불": "Fire", "물": "Water", "땅": "Earth",
    "순간": "Instant", "칸": "tiles",
    "언데드": "Undead",
}
spell_desc_tw = {
    "種類": "Type", "相性": "Alignment", "消耗": "Cost",
    "持續時間": "Duration", "對象": "Target",
    "治癒": "Healing", "攻擊": "Attack", "輔助": "Support",
    "風": "Wind", "火": "Fire", "水": "Water", "地": "Earth",
    "瞬間": "Instant", "格": "tiles",
    "魔力": "MP", "體力": "HP",
    "不死系": "Undead",
}

def camel_to_readable(s):
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    result = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', result)
    return result

def get_spell_name(skill_id):
    if skill_id in sql_skills:
        raw = sql_skills[skill_id]
        if raw in spell_name_map:
            return spell_name_map[raw]
        return camel_to_readable(raw)
    return None

def translate_spell_desc(text):
    result = text
    for kr, en in spell_desc_kr.items():
        result = result.replace(kr, en)
    for tw, en in spell_desc_tw.items():
        result = result.replace(tw, en)
    return result


def lookup(kr, tw, rid=0):
    """Try all sources to find English translation."""
    # Exact manual TW match
    if tw in manual:
        return manual[tw]
    # KR match in string TBL
    if kr in str_kr2en:
        return str_kr2en[kr]
    # KR match in desc TBL
    if kr in desc_kr2en:
        return desc_kr2en[kr]
    # CN/TW match
    if tw in cn2en:
        return cn2en[tw]
    # SQL desc_id
    if rid and rid in sql_desc:
        return sql_desc[rid]
    # Try TW compound names with ^
    if '^' in tw:
        parts = tw.split('^')
        en_parts = []
        for p in parts:
            ep = manual.get(p) or cn2en.get(p)
            if ep:
                en_parts.append(ep)
            else:
                en_parts.append(p)
        if any(ep != p for ep, p in zip(en_parts, parts)):
            return '^'.join(en_parts)
    return None


print(f"  String KR->EN: {len(str_kr2en)}")
print(f"  Desc KR->EN: {len(desc_kr2en)}")
print(f"  CN->EN: {len(cn2en)}")
print(f"  SQL desc: {len(sql_desc)}")
print(f"  SQL skills: {len(sql_skills)}")
print(f"  SQL NPCs: {len(sql_npc)}")
print(f"  Manual: {len(manual)}")

# ============================================================
# STRINGS
# ============================================================
print("\n=== STRINGS (file_00083) ===")
with open(os.path.join(OUT_DIR, "file_00083.csv"), 'r', encoding='utf-8-sig') as f:
    content = f.read()
lines = content.split('\n')
header = lines[0]
ncols = len(header.strip().split(','))
new_lines = [header]
changes = 0
total = 0

for line in lines[1:]:
    if not line.strip():
        new_lines.append(line)
        continue
    parts = line.split(',', ncols-1)
    if len(parts) < ncols:
        new_lines.append(line)
        continue
    has_cr = line.endswith('\r')
    kr = parts[3].rstrip('\r') if ncols >= 5 else ''
    tw = parts[-1].rstrip('\r')
    if not tw or tw.startswith('string'):
        new_lines.append(line)
        continue
    has_cn = any('\u4e00' <= c <= '\u9fff' for c in tw)
    if not has_cn:
        new_lines.append(line)
        continue
    total += 1
    
    en_val = lookup(kr, tw)
    if en_val and ',' not in en_val and len(en_val) < 500:
        parts[-1] = en_val + ('\r' if has_cr else '')
        changes += 1
    
    new_lines.append(','.join(parts))

print(f"  Translated: {changes}/{total}")
mod = '\n'.join(new_lines)
mod_bytes = b'\xef\xbb\xbf' + mod.encode('utf-8')
compress_fit(mod_bytes, os.path.join(ORIG_DIR, 'file_00083.bin'),
             os.path.join(OUT_DIR, "string_en_padded.zst"), "strings")

# ============================================================
# ITEMS
# ============================================================
print("\n=== ITEMS (file_00084) ===")
with open(os.path.join(OUT_DIR, "file_00084.csv"), 'r', encoding='utf-8-sig') as f:
    content = f.read()
lines = content.split('\n')
header = lines[0]
ncols = len(header.strip().split(','))
new_lines = [header]
changes = 0
total = 0

for line in lines[1:]:
    if not line.strip():
        new_lines.append(line)
        continue
    parts = line.split(',', ncols-1)
    if len(parts) < ncols:
        new_lines.append(line)
        continue
    has_cr = line.endswith('\r')
    rid = int(parts[0]) if parts[0].isdigit() else 0
    kr = parts[2].rstrip('\r') if ncols >= 4 else ''
    tw = parts[-1].rstrip('\r')
    if not tw or tw.startswith('desc'):
        new_lines.append(line)
        continue
    has_cn = any('\u4e00' <= c <= '\u9fff' for c in tw)
    if not has_cn:
        new_lines.append(line)
        continue
    total += 1
    
    en_val = lookup(kr, tw, rid)
    if en_val and ',' not in en_val and len(en_val) < 500:
        parts[-1] = en_val + ('\r' if has_cr else '')
        changes += 1
    
    new_lines.append(','.join(parts))

print(f"  Translated: {changes}/{total}")
mod = '\n'.join(new_lines)
mod_bytes = b'\xef\xbb\xbf' + mod.encode('utf-8')
compress_fit(mod_bytes, os.path.join(ORIG_DIR, 'file_00084.bin'),
             os.path.join(OUT_DIR, "items_en_padded.zst"), "items")

# ============================================================
# SPELLS
# ============================================================
print("\n=== SPELLS (file_00085) ===")
with open(os.path.join(OUT_DIR, "file_00085.csv"), 'r', encoding='utf-8-sig') as f:
    content = f.read()
lines = content.split('\n')
header = lines[0]
ncols = len(header.strip().split(','))
new_lines = [header]
name_changes = 0
desc_changes = 0
total_names = 0
total_descs = 0

for line in lines[1:]:
    if not line.strip():
        new_lines.append(line)
        continue
    parts = line.split(',', ncols-1)
    if len(parts) < ncols:
        new_lines.append(line)
        continue
    has_cr = line.endswith('\r')
    sid = int(parts[0]) if parts[0].isdigit() else 0
    kr = parts[2].rstrip('\r') if ncols >= 4 else ''
    tw = parts[-1].rstrip('\r')
    
    if not tw:
        new_lines.append(line)
        continue
    
    has_cn = any('\u4e00' <= c <= '\u9fff' for c in tw)
    has_kr = any('\uac00' <= c <= '\ud7a3' for c in tw) or any('\uac00' <= c <= '\ud7a3' for c in kr)
    
    if not has_cn and not has_kr:
        new_lines.append(line)
        continue
    
    if sid % 2 == 1:
        total_names += 1
        skill_id = (sid + 1) // 2
        en_name = get_spell_name(skill_id)
        if en_name:
            parts[-1] = en_name + ('\r' if has_cr else '')
            if ncols >= 4 and has_kr:
                parts[2] = en_name
            name_changes += 1
    else:
        total_descs += 1
        translated = translate_spell_desc(tw)
        if translated != tw:
            parts[-1] = translated + ('\r' if has_cr else '')
            desc_changes += 1
            if ncols >= 4 and kr:
                parts[2] = translate_spell_desc(parts[2].rstrip('\r'))
    
    new_lines.append(','.join(parts))

print(f"  Names translated: {name_changes}/{total_names}")
print(f"  Descs translated: {desc_changes}/{total_descs}")
mod = '\n'.join(new_lines)
mod_bytes = b'\xef\xbb\xbf' + mod.encode('utf-8')
compress_fit(mod_bytes, os.path.join(ORIG_DIR, 'file_00085.bin'),
             os.path.join(OUT_DIR, "spells_en_padded.zst"), "spells")

# ============================================================
# DIALOGUE - work directly on the original blob to preserve structure
# ============================================================
print("\n=== DIALOGUE (file_00086) ===")
orig_blob_path = os.path.join(ORIG_DIR, 'file_00086.bin')
with open(orig_blob_path, 'rb') as f:
    orig_zst = f.read()
orig_data = dctx.decompress(orig_zst, max_output_size=50*1024*1024)

# Build dialogue-specific exact replacements (TW -> EN, only safe full-field swaps)
# These must be the EXACT byte sequences found in the blob and same length or we pad
dialogue_replacements = {}
for tw_text, en_text in manual.items():
    tw_bytes = tw_text.encode('utf-8')
    en_bytes = en_text.encode('utf-8')
    # Only replace if the TW text appears in the blob and EN is not longer
    if tw_bytes in orig_data and len(en_bytes) <= len(tw_bytes):
        # Pad EN to same length with spaces
        padded_en = en_bytes + b' ' * (len(tw_bytes) - len(en_bytes))
        dialogue_replacements[tw_bytes] = padded_en

# Apply replacements to preserve exact blob size
mod_data = bytearray(orig_data)
changes = 0
for tw_bytes, en_bytes in sorted(dialogue_replacements.items(), key=lambda x: -len(x[0])):
    # Only replace if it's a standalone term (not inside a larger word)
    # Skip very short terms (1-2 chars) that could be part of other words
    if len(tw_bytes) < 6:  # Less than 2 Chinese characters
        continue
    idx = 0
    while True:
        pos = bytes(mod_data).find(tw_bytes, idx)
        if pos == -1:
            break
        mod_data[pos:pos+len(tw_bytes)] = en_bytes
        changes += 1
        idx = pos + len(en_bytes)

print(f"  Byte-level replacements: {changes}")
print(f"  Size preserved: {len(mod_data) == len(orig_data)}")

# Recompress with same size constraint
mod_bytes = bytes(mod_data)
compress_fit(mod_bytes, orig_blob_path,
             os.path.join(OUT_DIR, "dialogue_en_padded.zst"), "dialogue")

print("\nDone!")
