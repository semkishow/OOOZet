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

from common import config, debacktick, event_listener

def _sanitize_content(message):
  return debacktick(message).replace('\x1b', '')

def _render_content(content):
  if content == '': return ''
  return '```ansi\n' + content + '\n```'

def _render_attachments(attachments):
  return ' '.join([attachment.url for attachment in attachments])

def _render_embeds(embeds):
  return '\n'.join([f'{embed.title}\n{embed.description}' for embed in embeds])

async def print_message_deleted(msg):
  embed = discord.Embed(title='Usunięto wiadomość', colour=discord.Colour(0xff0000))
  embed.add_field(name=f'Użytkownik: ', value=f'<@{msg.author.id}>')
  embed.add_field(name=f'Kanał: ', value=f'<#{msg.channel.id}>')
  embed.add_field(name=f'', value=_render_content(_sanitize_content(msg.content)), inline=False)
  if msg.poll:
    answers = ' '.join([f'\nOdpowiedź: `{answer.media.text}`' for answer in msg.poll.answers])
    embed.add_field(name='Ankieta: ', value=f'Pytanie: `{msg.poll.question}`{answers}', inline=False)
  if len(msg.embeds) > 0:
    embed.add_field(name='Embedy: ', value=_render_embeds(msg.embeds), inline=False)
  if msg.reference:
    referenced_msg = await bot.get_channel(msg.reference.channel_id).fetch_message(msg.reference.message_id)
    embed.add_field(name='Przywołana wiadomość: ', value=referenced_msg.jump_url, inline=False)
  if msg.attachments:
    if len(msg.attachments) > 0:
      embed.set_image(url=msg.attachments[0].url)
    embed.add_field(name=f'Pliki: ', value=f'{_render_attachments(msg.attachments)}', inline=False)
  embed.add_field(name='', value=msg.jump_url, inline=False)
  await bot.get_channel(config['staff_logs_channel']).send(embed=embed)

@event_listener
async def on_message_delete(msg):
  await print_message_deleted(msg)

ANSI_RED = '\x1b[31m'
ANSI_GREEN = '\x1b[32m'
ANSI_CLEAR = '\x1b[0m'

# This diff only shows characters added to `after` and completely skips characters removed from `before`
# This is expected behaviour for logging edits, but may be unwanted in other use cases
def _message_diff(before, after, diff_color: str = ANSI_GREEN):
  res = list(before)
  for i, s in enumerate(difflib.ndiff(before, after)):
    if s[0] == '-':
      res[i] = ''
    elif s[0] == '+':
      res.insert(i, f'{diff_color}{s[-1]}{ANSI_CLEAR}')
  return _render_content(''.join(res))

@event_listener
async def on_message_edit(before, after):
  msg = before
  member = msg.author
  if member.bot or msg.is_system() or msg.guild is None or msg.guild.id != config['guild']:
    return

  before.content = _sanitize_content(before.content)
  after.content = _sanitize_content(after.content)

  embed = discord.Embed(title='Zedytowano wiadomość', colour=discord.Colour(0x7777ff))
  embed.add_field(name=f'Użytkownik: ', value=f'<@{msg.author.id}>')
  embed.add_field(name=f'Kanał: ', value=f'<#{msg.channel.id}>')
  if before.content != after.content:
    embed.add_field(name=f'Przed: ', value=f'{_message_diff(after.content, before.content, diff_color=ANSI_RED)}', inline=False)
    embed.add_field(name=f'Po: ', value=f'{_message_diff(before.content, after.content, diff_color=ANSI_GREEN)}', inline=False)
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
    embed.add_field(name=f'Pliki przed: ', value=f'{_render_attachments(before.attachments)}', inline=False)
    embed.add_field(name=f'Pliki po: ', value=f'{_render_attachments(after.attachments)}', inline=False)
  embed.add_field(name='', value=f'{after.jump_url}', inline=False)
  await bot.get_channel(config['staff_logs_channel']).send(embed=embed)

@event_listener
async def on_member_update(before, after):
  if before.nick != after.nick:
    embed = discord.Embed(title='Zmieniono nick użytkownika', colour=discord.Colour(0x777777))
    embed.add_field(name=f'Użytkownik: ', value=f'<@{after.id}>')
    if before.nick:
      embed.add_field(name='Nick przed: ', value=f'{before.nick}', inline=False)
    else:
      embed.add_field(name='Nick przed: ', value=f'{before.global_name}', inline=False)
    if after.nick:
      embed.add_field(name='Nick po: ', value=f'{after.nick}', inline=False)
    else:
      embed.add_field(name='Nick po: ', value=f'{after.global_name}', inline=False)
  await bot.get_channel(config['staff_logs_channel']).send(embed=embed)
