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

from common import config, debacktick, event_listener, RichText, RichChar

def render_attachments(attachments):
  return ' '.join([attachment.url for attachment in attachments])

async def print_message_deleted(msg):
  embed = discord.Embed(title='Usunięto wiadomość', colour=discord.Colour(0xff0000))
  embed.add_field(name=f'Użytkownik: ', value=f'<@{msg.author.id}>')
  embed.add_field(name=f'Kanał: ', value=f'<#{msg.channel.id}>')
  embed.add_field(name=f'', value=f'{msg.content}', inline=False)
  if msg.poll:
    answers = ' '.join([f'\nOdpowiedź: `{answer.media.text}`' for answer in msg.poll.answers])
    embed.add_field(name='Ankieta: ', value=f'Pytanie: `{msg.poll.question}`{answers}', inline=False)
  if msg.attachments:
    embed.add_field(name=f'Pliki: ', value=f'{render_attachments(msg.attachments)}', inline=False)
  embed.add_field(name='', value=f'{msg.jump_url}', inline=False)
  await bot.get_channel(config['staff_logs_channel']).send(embed=embed)

@event_listener
async def on_message_delete(msg):
  member = msg.author
  if member.bot or msg.is_system() or msg.guild is None or msg.guild.id != config['guild']:
    return
  await print_message_deleted(msg)

# This diff only shows characters added to `after` and completely skips characters removed from `before`
# This is expected behaviour for logging edits, but may be unwanted in other use cases
def _message_diff(before, after):
  before = debacktick(before)
  after = debacktick(after)
  res = RichText(before)
  for i, s in enumerate(difflib.ndiff(before, after)):
    if s[0] == '-':
      res.text[i] = RichChar()
    elif s[0] == '+':
      res.text.insert(i, RichChar(s[-1], underline=True))
  return str(res)

@event_listener
async def on_message_edit(before, after):
  msg = before
  member = msg.author
  if member.bot or msg.is_system() or msg.guild is None or msg.guild.id != config['guild']:
    return

  embed = discord.Embed(title='Zedytowano wiadomość', colour=discord.Colour(0x7777ff))
  embed.add_field(name=f'Użytkownik: ', value=f'<@{msg.author.id}>')
  embed.add_field(name=f'Kanał: ', value=f'<#{msg.channel.id}>')
  if before.content != after.content:
    embed.add_field(name=f'Przed: ', value=f'{_message_diff(after.content, before.content)}', inline=False)
    embed.add_field(name=f'Po: ', value=f'{_message_diff(before.content, after.content)}', inline=False)
  if before.attachments != after.attachments:
    embed.add_field(name=f'Pliki przed: ', value=f'{render_attachments(before.attachments)}', inline=False)
    embed.add_field(name=f'Pliki po: ', value=f'{render_attachments(after.attachments)}', inline=False)
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
