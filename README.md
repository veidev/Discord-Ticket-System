<div align="center">

<img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=28&duration=3200&pause=900&color=5865F2&center=true&vCenter=true&width=600&lines=Discord+Bot+Ticket+System;Discord.py+%7C+Private+Channels;Transcript+%2B+Panel+Button" alt="Typing SVG" />

<br/>

<img src="https://img.shields.io/badge/Discord.py-2.x-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord.py" />
<img src="https://img.shields.io/badge/Tickets-Private%20channels-57F287?style=for-the-badge" alt="Tickets" />
<img src="https://img.shields.io/badge/Transcript-HTML-ED4245?style=for-the-badge" alt="Transcript" />

</div>

---

## Ne bu?

**Sea Bot** ana projesinden ayrılmış destek bileti (ticket) modülü: butonlu panel, kullanıcıya özel metin kanalı, claim / kapat, HTML transcript ve log kanalına gönderim.

---

## Özellikler

| | |
| --- | --- |
| Panel | Kalıcı **Open Ticket** butonu (yeniden başlatmada çalışır) |
| Kanal | `ticket-kullaniciadi` özel izinlerle kategori altında |
| Yetki | Moderatör veya `ticket_support_role` ile claim / kapat |
| Kapatma | `.close` veya **Close Ticket** butonu → HTML transcript |

---

## Kurulum

```bash
pip install -r requirements.txt
```

`ticket_cog.py` dosyasını ana bot klasörüne kopyala. Ana botunda `bot = commands.Bot(...)` tanımından **sonra**:

```python
from ticket_cog import TicketCog

bot.add_cog(
    TicketCog(
        bot,
        get_guild_config=get_guild_config,
        save_config=save_config,
        prefix=PREFIX,
        allowed_guild_ids=ALLOWED_GUILD_IDS,  # frozenset veya set
        is_moderator=is_member_moderator,
    )
)
```

`get_guild_config(guild_id)` dönen sözlük şu anahtarları desteklemeli (yoksa `None`):

- `ticket_category_id`
- `ticket_log_channel_id`
- `ticket_support_role_id`

---

## Komutlar

| Komut | Açıklama |
| --- | --- |
| `{prefix}ticket [sebep]` | Bilet kanalı aç |
| `{prefix}ticket-panel [#kanal]` | Butonlu panel mesajı |
| `{prefix}close [sebep]` | Transcript + kanalı sil |
| `{prefix}ticket-config` | Kategori / log / destek rolü |

> Ana Sea Bot projende bu komutlar eskiden `.config ticket-*` altındaydı; burada çakışmayı önlemek için **`ticket-config`** grubu kullanıldı. İstersen bu üç alt komutu kendi `config` grubuna taşıyabilirsin.

---

## Gerekli bot izinleri

Kanal oluşturma, mesaj gönderme, kanal yönetimi, transcript dosyası yükleme ve (isteğe bağlı) kanal silme.

---

## Lisans

Sea Bot projesiyle aynı kullanım koşullarına tabi tutabilirsin; kendi reponda MIT vb. belirtmek sana kalmış.

---

<div align="center">

**Made with** <img src="https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f3ab.svg" width="18" alt="ticket" /> **for Discord communities**

</div>
