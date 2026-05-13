<div align="center">

<img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=28&duration=3200&pause=900&color=5865F2&center=true&vCenter=true&width=600&lines=Discord+Ticket+System;Discord.py+%7C+Private+Channels;Transcript+%2B+Panel+Button" alt="Typing SVG" />

<br/>

<img src="https://img.shields.io/badge/Discord.py-2.x-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord.py" />
<img src="https://img.shields.io/badge/Tickets-Private%20channels-57F287?style=for-the-badge" alt="Tickets" />
<img src="https://img.shields.io/badge/Transcript-HTML-ED4245?style=for-the-badge" alt="Transcript" />

</div>

---

## What is this?

A **support ticket** module split from the main **Sea Bot** project: button panel, per-user private text channel, claim/close, HTML transcript upload, and optional log channel delivery.

---

## Features

| | |
| --- | --- |
| Panel | Persistent **Open Ticket** button (survives bot restarts) |
| Channel | `ticket-username` under a category with custom overwrites |
| Permissions | Claim/close by moderators or `ticket_support_role` |
| Close | `{prefix}close` or **Close Ticket** button → HTML transcript |

---

## Setup

```bash
pip install -r requirements.txt
```

Copy `ticket_cog.py` into your main bot folder. **After** `bot = commands.Bot(...)`:

```python
from ticket_cog import TicketCog

bot.add_cog(
    TicketCog(
        bot,
        get_guild_config=get_guild_config,
        save_config=save_config,
        prefix=PREFIX,
        allowed_guild_ids=ALLOWED_GUILD_IDS,  # frozenset or set
        is_moderator=is_member_moderator,
    )
)
```

`get_guild_config(guild_id)` must return a dict that may include (use `None` if unset):

- `ticket_category_id`
- `ticket_log_channel_id`
- `ticket_support_role_id`

---

## Commands

| Command | Description |
| --- | --- |
| `{prefix}ticket [reason]` | Open a ticket channel |
| `{prefix}ticket-panel [#channel]` | Post the button panel |
| `{prefix}close [reason]` | Save transcript and delete the channel |
| `{prefix}ticket-config` | Category / log channel / support role |

> In the original Sea Bot these lived under `.config ticket-*`. This package uses a **`ticket-config`** group so it does not clash with your existing `config` command group. You can move the three subcommands into your own group if you prefer.

---

## Bot permissions

Create channels, send messages, manage channels, attach files (transcript), and delete channels when closing tickets.

---

## License

Use the same terms as your Sea Bot project, or pick a license (e.g. MIT) for this repo.

---

<div align="center">

**Made with** <img src="https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f3ab.svg" width="18" alt="ticket" /> **for Discord communities**

</div>
