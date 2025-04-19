import os
import discord
import random
from discord.ext import commands
from enum import Enum
from myserver import server_on

# อิโมจิสำหรับแสดงสถานะ
HP_EMOJI = '❤️'
MP_EMOJI = '💠'
MENTAL_EMOJI = '🧠'
DICE_EMOJI = '🎲'

# ประเภทตัวละคร
class CharacterType(Enum):
    HERO = "ฮีโร่"
    ANTI_HERO = "ผู้ไม่หวังดี"
    VILLAIN = "วายร้าย"
    MONSTER = "สัตว์ประหลาด"

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# คลาสตัวละคร
class Character:
    def __init__(self, name, char_type, hp, mp, mental, speed):
        self.name = name
        self.char_type = char_type
        self.max_hp = hp
        self.hp = hp
        self.max_mp = mp
        self.mp = mp
        self.mental = mental
        self.speed = speed
        self.effects = []
        self.team = self._determine_team()
        self.owner = None
        self.attack_count = 1  # จำนวนครั้งที่โจมตีได้ในหนึ่งตา
    
    def _determine_team(self):
        if self.char_type in [CharacterType.HERO, CharacterType.ANTI_HERO]:
            return "ฝ่ายฮีโร่"
        return "ฝ่ายวายร้าย"
    
    def get_icon(self):
        icons = {
            CharacterType.HERO: "🦸",
            CharacterType.ANTI_HERO: "🦹",
            CharacterType.VILLAIN: "👿",
            CharacterType.MONSTER: "👹"
        }
        return icons.get(self.char_type, "👤")
    
    def calculate_attack_bonus(self, target):
        """คำนวณโบนัสการโจมตีตามประเภทตัวละคร"""
        type_advantages = {
            CharacterType.HERO: {
                'strong_against': [CharacterType.VILLAIN],
                'weak_against': [CharacterType.ANTI_HERO]
            },
            CharacterType.ANTI_HERO: {
                'strong_against': [CharacterType.HERO],
                'weak_against': [CharacterType.MONSTER]
            },
            CharacterType.VILLAIN: {
                'strong_against': [CharacterType.ANTI_HERO],
                'weak_against': [CharacterType.HERO]
            },
            CharacterType.MONSTER: {
                'strong_against': [CharacterType.ANTI_HERO],
                'weak_against': [CharacterType.VILLAIN]
            }
        }
        
        advantage = type_advantages.get(self.char_type, {})
        
        if target.char_type in advantage.get('strong_against', []):
            return 1.5  # โจมตีได้แรงขึ้น 50%
        elif target.char_type in advantage.get('weak_against', []):
            return 0.7  # โจมตีได้อ่อนลง 30%
        return 1.0  # ไม่มีผล

# คลาสการต่อสู้
class Battle:
    def __init__(self):
        self.participants = []
        self.turn_order = []
        self.current_turn = 0
        self.is_active = False
        self.narrative = []
    
    def add_participant(self, character):
        self.participants.append(character)
        self.update_turn_order()
    
    def update_turn_order(self):
        self.turn_order = sorted(self.participants, key=lambda x: x.speed, reverse=True)
    
    def next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.turn_order)
        return self.turn_order[self.current_turn]
    
    def get_target(self, target_name):
        for char in self.participants:
            if char.name.lower() == target_name.lower():
                return char
        return None
    
    def get_characters_by_owner(self, user_id):
        return [char for char in self.participants if char.owner == user_id]
    
    def get_team_members(self, team_name):
        return [char for char in self.participants if char.team == team_name and char.hp > 0]
    
    def get_status_emoji(self, current, max):
        filled = round(current / max * 10) if max > 0 else 0
        return '🟥' * filled + '⬛' * (10 - filled)
    
    def get_status_embed(self):
        embed = discord.Embed(title="⚔️ สถานะการต่อสู้ ⚔️", color=0x00ff00)
        
        heroes = self.get_team_members("ฝ่ายฮีโร่")
        if heroes:
            hero_status = []
            for char in heroes:
                status = f"{char.get_icon()} {char.name} ({char.char_type.value})\n"
                status += f"{HP_EMOJI} {char.hp}/{char.max_hp} {self.get_status_emoji(char.hp, char.max_hp)}\n"
                status += f"{MP_EMOJI} {char.mp}/{char.max_mp} {self.get_status_emoji(char.mp, char.max_mp)}\n"
                status += f"{MENTAL_EMOJI} {char.mental}/100"
                if char.effects:
                    status += f"\n🔮 ผลกระทบ: {', '.join(char.effects)}"
                hero_status.append(status)
            
            embed.add_field(name="🛡️ ฝ่ายฮีโร่ 🛡️", value="\n\n".join(hero_status), inline=False)
        
        villains = self.get_team_members("ฝ่ายวายร้าย")
        if villains:
            villain_status = []
            for char in villains:
                status = f"{char.get_icon()} {char.name} ({char.char_type.value})\n"
                status += f"{HP_EMOJI} {char.hp}/{char.max_hp} {self.get_status_emoji(char.hp, char.max_hp)}\n"
                status += f"{MP_EMOJI} {char.mp}/{char.max_mp} {self.get_status_emoji(char.mp, char.max_mp)}\n"
                status += f"{MENTAL_EMOJI} {char.mental}/100"
                if char.effects:
                    status += f"\n🔮 ผลกระทบ: {', '.join(char.effects)}"
                villain_status.append(status)
            
            embed.add_field(name="💀 ฝ่ายวายร้าย 💀", value="\n\n".join(villain_status), inline=False)
        
        if self.turn_order:
            current_char = self.turn_order[self.current_turn]
            embed.set_footer(text=f"ตาปัจจุบัน: {current_char.get_icon()} {current_char.name}")
        
        return embed
    
    def check_battle_end(self):
        heroes_alive = any(char.team == "ฝ่ายฮีโร่" and char.hp > 0 for char in self.participants)
        villains_alive = any(char.team == "ฝ่ายวายร้าย" and char.hp > 0 for char in self.participants)
        
        if not heroes_alive:
            return "ฝ่ายวายร้ายชนะ!"
        elif not villains_alive:
            return "ฝ่ายฮีโร่ชนะ!"
        return None
    
    def add_narrative(self, text):
        self.narrative.append(text)
        if len(self.narrative) > 5:
            self.narrative.pop(0)
    
    def get_narrative(self):
        return "\n".join(f"• {line}" for line in self.narrative[-3:]) if self.narrative else "การต่อสู้เริ่มต้นขึ้น..."
    def add_participant(self, character):
        """เพิ่มตัวละครและอัพเดทลำดับการเล่น"""
        self.participants.append(character)
        self.update_turn_order()
        
        # ถ้าการต่อสู้เริ่มแล้วและนี่เป็นตัวละครแรกของทีม
        if self.is_active:
            team = character.team
            team_members = self.get_team_members(team)
            if len(team_members) == 1:
                self.add_narrative(f"⚔️ {character.get_icon()} {character.name} เข้าร่วมการต่อสู้เป็นฝ่าย {team}!")
    
    def update_turn_order(self):
        """อัพเดทลำดับการเล่นโดยเรียงตามความเร็ว"""
        # กรองเฉพาะตัวละครที่ HP > 0
        alive_participants = [char for char in self.participants if char.hp > 0]
        
        # เรียงลำดับใหม่
        self.turn_order = sorted(alive_participants, key=lambda x: x.speed, reverse=True)
        
        # ปรับ current_turn ให้อยู่ในขอบเขตที่ถูกต้อง
        if self.turn_order and self.current_turn >= len(self.turn_order):
            self.current_turn = max(0, len(self.turn_order) - 1)
    def apply_mental_effects(self, attacker, defender):
        """ประมวลผลผลกระทบจากจิตใจ"""
        mental_diff = attacker.mental - defender.mental
        
        # ถ้าจิตใจแตกต่างมากกว่า 30 หน่วย
        if mental_diff > 30:
            defender.effects.append("หวาดกลัว")
            self.add_narrative(f"😨 {defender.name} รู้สึกหวาดกลัวจากความต่างของจิตใจ!")
        elif mental_diff < -30:
            attacker.effects.append("ลังเล")
            self.add_narrative(f"🤔 {attacker.name} ลังเลเนื่องจากจิตใจต่ำกว่าเป้าหมาย!")

current_battle = Battle()

@bot.event
async def on_ready():
    print(f'บอทพร้อมใช้งานในชื่อ {bot.user}')
    await bot.change_presence(activity=discord.Game(name="พิมพ์ !ช่วยเหลือ"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("⚠️ ไม่พบคำสั่งนี้ กรุณาพิมพ์ !ช่วยเหลือ เพื่อดูคำสั่งทั้งหมด")
    else:
        print(f'เกิดข้อผิดพลาด: {error}')
@bot.command(name='สร้างตัวละคร')
async def create_character(ctx, char_type: str, name: str, hp: int, mp: int, mental: int, speed: int):
    """สร้างตัวละครใหม่ (ฮีโร่/ผู้ไม่หวังดี/วายร้าย/สัตว์ประหลาด)"""
    try:
        # สร้าง mapping สำหรับคำไทย
        type_mapping = {
            "ฮีโร่": "HERO",
            "ผู้ไม่หวังดี": "ANTI_HERO",
            "วายร้าย": "VILLAIN",
            "สัตว์ประหลาด": "MONSTER"
        }
        
        # ตรวจสอบว่าผู้ใช้ป้อนคำไทยหรือภาษาอังกฤษ
        if char_type in type_mapping:
            char_type_enum = CharacterType[type_mapping[char_type]]
        else:
            # ถ้าไม่ใช่คำไทย ให้ลองแปลงเป็น enum โดยตรง
            char_type_enum = CharacterType[char_type.upper()]
            
    except KeyError:
        await ctx.send("⚠️ ประเภทตัวละครไม่ถูกต้อง! ใช้: ฮีโร่, ผู้ไม่หวังดี, วายร้าย หรือ สัตว์ประหลาด")
        return
    
    # ส่วนที่เหลือของฟังก์ชันเหมือนเดิม
    if current_battle.is_active:
        await ctx.send("⛔ ไม่สามารถสร้างตัวละครระหว่างการต่อสู้ได้!")
        return
    
    if any(char.name.lower() == name.lower() for char in current_battle.participants):
        await ctx.send("⚠️ มีตัวละครชื่อนี้อยู่แล้ว!")
        return
    
    character = Character(
        name=name,
        char_type=char_type_enum,
        hp=hp,
        mp=mp,
        mental=mental,
        speed=speed
    )
    
    if char_type_enum in [CharacterType.HERO, CharacterType.ANTI_HERO]:
        character.owner = ctx.author.id
    
    current_battle.add_participant(character)
    
    await ctx.send(
        f"✅ สร้างตัวละคร {char_type_enum.value} ชื่อ {name} สำเร็จ!\n"
        f"{HP_EMOJI} HP: {hp} | {MP_EMOJI} MP: {mp}\n"
        f"{MENTAL_EMOJI} จิตใจ: {mental} | 🏃 ความเร็ว: {speed}"
    )


@bot.command(name='ลบตัวละคร')
async def remove_character(ctx, name: str):
    """ลบตัวละครออกจากการต่อสู้"""
    # หาตัวละครจากชื่อ
    char_to_remove = None
    for char in current_battle.participants:
        if char.name.lower() == name.lower():
            char_to_remove = char
            break
    
    if not char_to_remove:
        await ctx.send(f"⚠️ ไม่พบตัวละครชื่อ '{name}'")
        return
    
    # ลบตัวละครออก
    current_battle.participants.remove(char_to_remove)
    
    # ถ้าตัวละครที่ลบอยู่ในลำดับการเล่น
    if char_to_remove in current_battle.turn_order:
        # หาตำแหน่งใน turn_order
        index = current_battle.turn_order.index(char_to_remove)
        
        # ลบออกจาก turn_order
        current_battle.turn_order.remove(char_to_remove)
        
        # ปรับ current_turn ถ้าจำเป็น
        if current_battle.current_turn >= index and current_battle.current_turn > 0:
            current_battle.current_turn -= 1
    
    await ctx.send(f"✅ ลบตัวละคร {char_to_remove.get_icon()} {char_to_remove.name} ออกเรียบร้อย")
    
    # อัพเดทสถานะ
    if current_battle.is_active:
        await ctx.send(embed=current_battle.get_status_embed())



@bot.command(name='เพิ่มตัวละคร')
async def add_character(ctx, char_type: str, name: str, hp: int, mp: int, mental: int, speed: int):
    """เพิ่มตัวละครใหม่ระหว่างเกม"""
    try:
        # สร้าง mapping สำหรับคำไทย
        type_mapping = {
            "ฮีโร่": "HERO",
            "ผู้ไม่หวังดี": "ANTI_HERO",
            "วายร้าย": "VILLAIN",
            "สัตว์ประหลาด": "MONSTER"
        }
        
        # ตรวจสอบว่าผู้ใช้ป้อนคำไทยหรือภาษาอังกฤษ
        if char_type in type_mapping:
            char_type_enum = CharacterType[type_mapping[char_type]]
        else:
            # ถ้าไม่ใช่คำไทย ให้ลองแปลงเป็น enum โดยตรง
            char_type_enum = CharacterType[char_type.upper()]
            
    except KeyError:
        await ctx.send("⚠️ ประเภทตัวละครไม่ถูกต้อง! ใช้: ฮีโร่, ผู้ไม่หวังดี, วายร้าย หรือ สัตว์ประหลาด")
        return
    
    if any(char.name.lower() == name.lower() for char in current_battle.participants):
        await ctx.send("⚠️ มีตัวละครชื่อนี้อยู่แล้ว!")
        return
    
    character = Character(
        name=name,
        char_type=char_type_enum,
        hp=hp,
        mp=mp,
        mental=mental,
        speed=speed
    )
    
    if char_type_enum in [CharacterType.HERO, CharacterType.ANTI_HERO]:
        character.owner = ctx.author.id
    
    current_battle.add_participant(character)
    
    # แจ้งเตือนการเพิ่มตัวละคร
    embed = discord.Embed(
        title=f"✅ เพิ่มตัวละคร {char_type_enum.value} สำเร็จ",
        description=(
            f"{character.get_icon()} **ชื่อ:** {name}\n"
            f"{HP_EMOJI} **HP:** {hp} | {MP_EMOJI} **MP:** {mp}\n"
            f"{MENTAL_EMOJI} **จิตใจ:** {mental} | 🏃 **ความเร็ว:** {speed}"
        ),
        color=0x00ff00
    )
    
    await ctx.send(embed=embed)
    
    # ถ้าการต่อสู้กำลังดำเนินอยู่ ให้อัพเดทสถานะ
    if current_battle.is_active:
        current_battle.update_turn_order()
        await ctx.send(embed=current_battle.get_status_embed())
        await ctx.send(f"**ตาปัจจุบัน:** {current_battle.turn_order[current_battle.current_turn].name}")

@bot.command(name='เริ่มการต่อสู้')
async def start_battle(ctx):
    """เริ่มการต่อสู้"""
    heroes = current_battle.get_team_members("ฝ่ายฮีโร่")
    villains = current_battle.get_team_members("ฝ่ายวายร้าย")
    
    if not heroes or not villains:
        await ctx.send("ต้องการตัวละครฝ่ายฮีโร่และฝ่ายวายร้ายอย่างน้อย 1 ตัวเพื่อเริ่มการต่อสู้!")
        return
    
    current_battle.is_active = True
    current_battle.update_turn_order()
    
    # แนะนำทีม
    hero_names = ", ".join([f"{char.get_icon()} {char.name}" for char in heroes])
    villain_names = ", ".join([f"{char.get_icon()} {char.name}" for char in villains])
    
    turn_order = " → ".join([f"{char.get_icon()} {char.name}" for char in current_battle.turn_order])
    
    embed = discord.Embed(
        title="⚔️ การต่อสู้เริ่มต้นขึ้น! ⚔️",
        description=f"**ฝ่ายฮีโร่:** {hero_names}\n**ฝ่ายวายร้าย:** {villain_names}",
        color=0xff0000
    )
    embed.add_field(name="ลำดับตา", value=turn_order, inline=False)
    embed.set_footer(text=f"ตาแรก: {current_battle.turn_order[0].name}")
    
    await ctx.send(embed=embed)
    await ctx.send(embed=current_battle.get_status_embed())


@bot.command(name='โจมตี')
async def attack(ctx, target_name: str = None):
    """โจมตีเป้าหมาย"""
    if not current_battle.is_active:
        await ctx.send("⛔ ยังไม่ได้เริ่มการต่อสู้!")
        return
    
    current_char = current_battle.turn_order[current_battle.current_turn]
    
    possible_targets = [char for char in current_battle.participants 
                      if char.team != current_char.team and char.hp > 0]
    
    if not target_name:
        if len(possible_targets) == 1:
            target = possible_targets[0]
        else:
            target_list = "\n".join([f"- {char.name}" for char in possible_targets])
            await ctx.send(f"📝 โปรดระบุเป้าหมายจาก:\n{target_list}")
            return
    else:
        target = current_battle.get_target(target_name)
        if not target or target.team == current_char.team:
            await ctx.send("⚠️ เป้าหมายไม่ถูกต้อง!")
            return
    
    # คำนวณค่าต่างๆ สำหรับการโจมตี
    roll = random.randint(1, 20)
    
    # ผลจากความเร็ว (โอกาสโจมตีหลายครั้ง)
    attack_count = 1
    if current_char.speed > target.speed + 10:
        attack_count = 2
    if current_char.speed > target.speed + 20:
        attack_count = 3
    
    # ผลจาก MP (เพิ่มความเสียหาย)
    mp_bonus = 1 + (current_char.mp / current_char.max_mp) * 0.5  # โบนัสสูงสุด 1.5 เท่า
    
    # ผลจากจิตใจ (ความแม่นยำ)
    accuracy = 0.5 + (current_char.mental / 200)  # 50%-100% จากจิตใจ
    
    total_damage = 0
    attack_details = []
    
    for _ in range(attack_count):
        # ตรวจสอบความแม่นยำ
        if random.random() > accuracy:
            attack_details.append("💨 โจมตีพลาด!")
            continue
        
        # คำนวณความเสียหายพื้นฐาน
        base_damage = max(1, roll // 3)
        damage = int(base_damage * mp_bonus)
        crit = roll == 20
        
        if crit:
            damage *= 2
            attack_details.append(f"💥 **Critical Hit!** ({damage} {HP_EMOJI})")
        elif roll >= 15:
            attack_details.append(f"✨ โจมตีอย่างมีประสิทธิภาพ! ({damage} {HP_EMOJI})")
        elif roll >= 10:
            attack_details.append(f"⚔️ โจมตีสำเร็จ ({damage} {HP_EMOJI})")
        elif roll >= 5:
            attack_details.append(f"🤕 โจมตีได้ผลน้อย ({damage} {HP_EMOJI})")
        
        total_damage += damage
    
    # ลด MP หลังโจมตี
    mp_cost = max(5, int(current_char.max_mp * 0.1))
    current_char.mp = max(0, current_char.mp - mp_cost)
    
    # เลือกคำกริยาโจมตี
    attack_verbs = {
        CharacterType.HERO: ["โจมตี", "เข้าต่อสู้กับ", "พุ่งเข้าหา"],
        CharacterType.ANTI_HERO: ["ซุ่มโจมตี", "จู่โจม", "ทำร้าย"],
        CharacterType.VILLAIN: ["กระหน่ำ", "สาปแช่ง", "โจมตี"],
        CharacterType.MONSTER: ["กัด", "ขย้ำ", "ถล่ม"]
    }
    verb = random.choice(attack_verbs.get(current_char.char_type, ["โจมตี"]))
    
    # สร้าง narrative
    narrative = f"{current_char.get_icon()} {current_char.name} {verb} {target.get_icon()} {target.name} ({DICE_EMOJI} {roll}):\n"
    narrative += "\n".join(attack_details)
    
    if total_damage > 0:
        target.hp = max(0, target.hp - total_damage)
        narrative += f"\nรวมความเสียหาย: {total_damage} {HP_EMOJI}"
        
        if target.hp <= 0:
            narrative += f"\n💀 {target.get_icon()} {target.name} ถูกกำจัดแล้ว!"
    
    current_battle.add_narrative(narrative)
    
    # ตรวจสอบผลการต่อสู้
    battle_result = current_battle.check_battle_end()
    if battle_result:
        embed = discord.Embed(
            title=f"🏆 {battle_result} 🏆",
            description=current_battle.get_narrative(),
            color=0x00ff00 if "ฮีโร่" in battle_result else 0xff0000
        )
        await ctx.send(embed=embed)
        current_battle.is_active = False
        return
    
    next_char = current_battle.next_turn()
    
    embed = discord.Embed(
        title="📜 อัพเดทการต่อสู้",
        description=current_battle.get_narrative(),
        color=0x7289da
    )
    await ctx.send(embed=embed)
    await ctx.send(embed=current_battle.get_status_embed())
    await ctx.send(f"**ตาถัดไป:** {next_char.get_icon()} {next_char.name}")

# เพิ่มคำสั่งเลือกตัวละคร
@bot.command(name='เลือก')
async def select_character(ctx, name: str):
    """เลือกตัวละครที่จะควบคุม"""
    char = current_battle.get_target(name)
    if not char:
        await ctx.send("⚠️ ไม่พบตัวละครนี้!")
        return
    
    # ในระบบใหม่นี้ ไม่จำเป็นต้องตรวจสอบ owner
    await ctx.send(f"✅ คุณเลือก {char.get_icon()} {char.name} แล้ว")
@bot.command(name='ลำดับ')
async def turn_order(ctx):
    """แสดงลำดับการเล่น"""
    if not current_battle.is_active:
        await ctx.send("⛔ ยังไม่ได้เริ่มการต่อสู้!")
        return
    
    order = "\n".join(
        f"{i+1}. {char.get_icon()} {char.name} (ความเร็ว: {char.speed})"
        for i, char in enumerate(current_battle.turn_order)
    )
    
    embed = discord.Embed(
        title="🔄 ลำดับการเล่น",
        description=order,
        color=0x00ffff
    )
    embed.set_footer(text=f"ตาปัจจุบัน: {current_battle.current_turn + 1}")
    await ctx.send(embed=embed)

@bot.command(name='สถานะ')
async def status(ctx):
    """แสดงสถานะการต่อสู้ปัจจุบัน"""
    if not current_battle.participants:
        await ctx.send("ℹ️ ยังไม่มีการต่อสู้")
        return
    
    await ctx.send(embed=current_battle.get_status_embed())

@bot.command(name='เป้าหมาย')
async def list_targets(ctx):
    """แสดงรายการเป้าหมาย"""
    user_chars = current_battle.get_characters_by_owner(ctx.author.id)
    if not user_chars:
        await ctx.send("⚠️ คุณไม่มีตัวละครในการต่อสู้นี้!")
        return
    
    team = user_chars[0].team
    enemies = [char for char in current_battle.participants 
               if char.team != team and char.hp > 0]
    
    if not enemies:
        await ctx.send("🎉 ไม่มีศัตรูเหลืออยู่แล้ว!")
        return
    
    embed = discord.Embed(title="🎯 เป้าหมายที่มี", color=0xff0000)
    for enemy in enemies:
        embed.add_field(
            name=f"{enemy.get_icon()} {enemy.name} ({enemy.char_type.value})",
            value=f"{HP_EMOJI} {enemy.hp}/{enemy.max_hp} {current_battle.get_status_emoji(enemy.hp, enemy.max_hp)}\nจิตใจ: {enemy.mental}/100",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name='ผ่าน')
async def skip_turn(ctx):
    """ข้ามตา"""
    if not current_battle.is_active:
        await ctx.send("⛔ ยังไม่ได้เริ่มการต่อสู้!")
        return
    
    current_char = current_battle.turn_order[current_battle.current_turn]
    if current_char.owner != ctx.author.id:
        await ctx.send("⏳ ยังไม่ใช่ตาของคุณ!")
        return
    
    next_char = current_battle.next_turn()
    current_battle.add_narrative(f"⏭️ {current_char.name} ข้ามตา")
    
    embed = discord.Embed(
        title="⏩ ข้ามตา",
        description=current_battle.get_narrative(),
        color=0xffff00
    )
    await ctx.send(embed=embed)
    await ctx.send(embed=current_battle.get_status_embed())
    await ctx.send(f"**ตาถัดไป:** {next_char.get_icon()} {next_char.name}")

@bot.command(name='จบการต่อสู้')
async def end_battle(ctx):
    """จบการต่อสู้"""
    current_battle.__init__()
    await ctx.send("═══════════════\nการต่อสู้จบลง\n═══════════════")

@bot.command(name='ช่วยเหลือ')
async def help_command(ctx):
    """แสดงคำสั่งทั้งหมดและวิธีการใช้งาน"""
    help_embed = discord.Embed(
        title="📜 คู่มือคำสั่ง RPG Battle Bot",
        description="คำสั่งทั้งหมดและวิธีการใช้งานบอทจัดการการต่อสู้แบบโรลเพลย์\n"
                    "────────────────────────────",
        color=0x7289da
    )
    
    # ส่วนคำสั่งสร้างและจัดการตัวละคร
    help_embed.add_field(
        name="🛠️ คำสั่งสร้างและจัดการตัวละคร",
        value=(
            "`!สร้างตัวละคร <ประเภท> <ชื่อ> <HP> <MP> <จิตใจ> <ความเร็ว>`\n"
            "สร้างตัวละครใหม่\n"
            "▶ ตัวอย่าง: `!สร้างตัวละคร ฮีโร่ อาเธอร์ 100 50 80 15`\n"
            "▶ ประเภทตัวละคร: ฮีโร่, ผู้ไม่หวังดี, วายร้าย, สัตว์ประหลาด\n\n"
            "!ลบตัวละคร <ชื่อตัวละคร>"
            "!พิ่มตัวละคร <ประเภท> <ชื่อ> <HP> <MP> <จิตใจ> <ความเร็ว>"
            
            
        
        ),
        inline=False
    )
    
    # ส่วนคำสั่งการต่อสู้
    help_embed.add_field(
        name="⚔️ คำสั่งการต่อสู้",
        value=(
            "`!เริ่มการต่อสู้`\n"
            "เริ่มเกมการต่อสู้เมื่อมีตัวละครทั้งสองฝ่าย\n"
            "▶ ตัวอย่าง: `!เริ่มการต่อสู้`\n\n"
            
            "`!โจมตี <ชื่อเป้าหมาย>`\n"
            "โจมตีศัตรู (ระบุชื่อเมื่อมีหลายศัตรู)\n"
            "▶ ตัวอย่าง: `!โจมตี มังกร` หรือ `!โจมตี` (เมื่อมีศัตรูคนเดียว)\n\n"
            
            "`!ผ่าน`\n"
            "ข้ามตาไป\n"
            "▶ ตัวอย่าง: `!ผ่าน`\n\n"
            
            "`!สถานะ`\n"
            "แสดงสถานะปัจจุบันของการต่อสู้\n"
            "▶ ตัวอย่าง: `!สถานะ`\n\n"
            
            "`!เป้าหมาย`\n"
            "แสดงรายการศัตรูทั้งหมด\n"
            "▶ ตัวอย่าง: `!เป้าหมาย`\n\n"
            
            "`!ลำดับ`\n"
            "แสดงลำดับการเล่นของตัวละคร\n"
            "▶ ตัวอย่าง: `!ลำดับ`\n"
            "────────────────────────────"
        ),
        inline=False
    )
    
    # ส่วนคำสั่งจัดการเกม
    help_embed.add_field(
        name="🎮 คำสั่งจัดการเกม",
        value=(
            "`!จบการต่อสู้`\n"
            "จบเกมการต่อสู้ปัจจุบัน\n"
            "▶ ตัวอย่าง: `!จบการต่อสู้`\n\n"
            
            "`!ช่วยเหลือ`\n"
            "แสดงคำสั่งทั้งหมดนี้\n"
            "▶ ตัวอย่าง: `!ช่วยเหลือ`"
        ),
        inline=False
    )
    help_embed.add_field(
        name="⚖️ ระบบความสัมพันธ์ตัวละคร",
        value=(
            "🦸 ฮีโร่ → 👿 วายร้าย (แรงขึ้น 50%)\n"
            "👿 วายร้าย → 🦹 ผู้ไม่หวังดี (แรงขึ้น 50%)\n"
            "🦹 ผู้ไม่หวังดี → 🦸 ฮีโร่ (แรงขึ้น 50%)\n"
            "👹 สัตว์ประหลาด → 🦹 ผู้ไม่หวังดี (แรงขึ้น 50%)\n\n"
            "หากโจมตีฝ่ายที่ได้เปรียบจะทำความเสียหายเพิ่ม 50%\n"
            "หากโจมตีฝ่ายที่เสียเปรียบจะทำความเสียหายลด 30%"
        ),
        inline=False
    )
    
    help_embed.add_field(
        name="📊 ผลของค่าสถานะ",
        value=(
            f"{MP_EMOJI} **MP:** ยิ่งมากยิ่งโจมตีแรง (สูงสุด 2 เท่า)\n"
            f"{MENTAL_EMOJI} **จิตใจ:** ส่งผลต่อความแม่นยำและป้องกันสถานะผิดปกติ\n"
            "🏃 **ความเร็ว:** อาจโจมตีได้หลายครั้งในหนึ่งตา\n"
            "💢 **ความต่างจิตใจ:** หากต่างมากกว่า 30 หน่วยจะมีผลพิเศษ"
        ),
        inline=False
    )
    
    # ข้อความท้าย
    help_embed.set_footer(
        text="📌 เคล็ดลับ:\n"
             "- ใช้ !สถานะ เพื่อดูสถานะปัจจุบัน\n"
             "- ใช้ !ลำดับ เพื่อดูว่าใครเล่นตาต่อไป\n"
             "- สามารถโจมตีโดยไม่ต้องเลือกตัวละครก่อนในระบบใหม่"
    )
    
    await ctx.send(embed=help_embed)


server_on()
# รันบอท



bot.run(os.getenv('DISCORD_TOKEN'))