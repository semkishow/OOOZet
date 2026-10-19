# OOOZet - Bot społeczności OOOZ
# Copyright (C) 2023-2026 Karol "digitcrusher" Łacina
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import discord, difflib
from io import BytesIO

from common import config, event_listener

EMBED_FIELD_LIMIT = 1024

def _sanitize_content(message):
  return message.replace('`', '\u2060`').replace('\x1b', '')

def _render_content(content):
  if content == '': return ''
  return '```ansi\n' + content + '\n```'

def _render_attachments(attachments):
  return '\n'.join([f'- {attachment.url}' for attachment in attachments])

def _render_embeds(embeds):
  return '\n'.join([f'{embed.title}\n{embed.description}' for embed in embeds])

async def log_deleted_message(msg):
  files = []
  embed = discord.Embed(title='Usunięto wiadomość', colour=discord.Colour.red())
  embed.add_field(name='Użytkownik: ', value=msg.author.mention)
  embed.add_field(name='Kanał: ', value=msg.channel.mention)

  content = _render_content(_sanitize_content(msg.content))
  if len(content) > EMBED_FIELD_LIMIT:
    files.append(discord.File(BytesIO(str.encode(msg.content)), "message.txt"))
  else:
    embed.add_field(name='', value=content, inline=False)

  if msg.poll:
    answers = '\n'.join([f'Odpowiedź: `{answer.media.text}`' for answer in msg.poll.answers])
    embed.add_field(name='Ankieta: ', value=f'Pytanie: `{msg.poll.question}`\n{answers}', inline=False)

  if len(msg.embeds) > 0:
    embed.add_field(name='Embedy: ', value=_render_embeds(msg.embeds), inline=False)

  if msg.reference:
    referenced_msg = await bot.get_channel(msg.reference.channel_id).fetch_message(msg.reference.message_id)
    embed.add_field(name='Przywołana wiadomość: ', value=referenced_msg.jump_url, inline=False)

  if msg.attachments:
    if len(msg.attachments) == 1:
      embed.set_image(url=msg.attachments[0].url)
    else:
      embed.add_field(name='Załączniki: ', value=_render_attachments(msg.attachments), inline=False)
  await bot.get_channel(config['staff_logs_channel']).send(embed=embed, files=files)

@event_listener
async def on_message_delete(msg):
  if msg.author.bot or msg.is_system() or msg.guild is None or msg.guild.id != config['guild']:
    return
  await log_deleted_message(msg)

ANSI_RED = '\x1b[31m'
ANSI_GREEN = '\x1b[32m'
ANSI_CLEAR = '\x1b[0m'

class AnsiChar:
  def __init__(self, text: str = '', *, color: str = ''):
    self.text = text
    self.color = color

class AnsiText:
  def __init__(self, plain_text: str = ''):
    self.text = [AnsiChar(c) for c in plain_text]

  def __str__(self):
    res = ''
    last_char = AnsiChar()
    for c in self.text:
      if c.color != last_char.color:
        res += ANSI_CLEAR + c.color
      res += c.text
      last_char = c
    res += ANSI_CLEAR
    return res

def _highlight_chars_added(before, after, *, color: str = ANSI_GREEN):
  res = AnsiText(before)
  for i, s in enumerate(difflib.ndiff(before, after)):
    if s[0] == '-':
      res.text[i] = AnsiChar()
    elif s[0] == '+':
      res.text.insert(i, AnsiChar(s[-1], color=color))
  return _render_content(str(res))

@event_listener
async def on_message_edit(before, after):
  if after.author.bot or after.is_system() or after.guild is None or after.guild.id != config['guild']:
    return

  before_content = _sanitize_content(before.content)
  after_content = _sanitize_content(after.content)

  files = []
  embed = discord.Embed(title='Zedytowano wiadomość', colour=discord.Colour.yellow())
  embed.add_field(name='Użytkownik: ', value=after.author.mention)
  embed.add_field(name='Wiadomość: ', value=after.jump_url)

  if before_content != after_content:
    before_rendered = _highlight_chars_added(after_content, before_content, color=ANSI_RED)
    if len(before_rendered) > EMBED_FIELD_LIMIT:
      files.append(discord.File(BytesIO(str.encode(before.content)), "before.txt"))
    else:
      embed.add_field(name='Przed: ', value=before_rendered, inline=False)

    after_rendered = _highlight_chars_added(before_content, after_content, color=ANSI_GREEN)
    if len(after_rendered) > EMBED_FIELD_LIMIT:
      files.append(discord.File(BytesIO(str.encode(after.content)), "after.txt"))
    else:
      embed.add_field(name='Po: ', value=after_rendered, inline=False)

  if before.embeds != after.embeds:
    embed.add_field(name='Embedy przed: ', value=_render_embeds(before.embeds), inline=False)
    embed.add_field(name='Embedy po: ', value=_render_embeds(after.embeds), inline=False)

  if before.reference != after.reference:
    reference_before = await bot.get_channel(before.reference.channel_id).fetch_message(before.reference.message_id)
    embed.add_field(name='Przywołana wiadomość przed: ', value=reference_before.jump_url, inline=False)
    reference_after = await bot.get_channel(after.reference.channel_id).fetch_message(after.reference.message_id)
    embed.add_field(name='Przywołana wiadomość po: ', value=reference_after.jump_url, inline=False)

  if before.attachments != after.attachments:
    if len(after.attachments) > 0:
      embed.set_image(url=after.attachments[0].url)
    elif len(before.attachments) > 0:
      embed.set_image(url=before.attachments[0].url)
    embed.add_field(name='Załączniki przed: ', value=_render_attachments(before.attachments), inline=False)
    embed.add_field(name='Załączniki po: ', value=_render_attachments(after.attachments), inline=False)

  await bot.get_channel(config['staff_logs_channel']).send(embed=embed, files=files)

@event_listener
async def on_member_update(before, after):
  if before.nick == after.nick: return

  embed = discord.Embed(title='Zmieniono nick użytkownika', colour=discord.Colour.light_gray())
  embed.add_field(name='Użytkownik: ', value=after.mention)
  if before.nick:
    embed.add_field(name='Nick przed: ', value=before.nick, inline=False)
  else:
    embed.add_field(name='Nick przed: ', value=before.global_name, inline=False)
  if after.nick:
    embed.add_field(name='Nick po: ', value=after.nick, inline=False)
  else:
    embed.add_field(name='Nick po: ', value=after.global_name, inline=False)
  await bot.get_channel(config['staff_logs_channel']).send(embed=embed)
