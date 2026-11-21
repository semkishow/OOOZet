# OOOZet - Bot społeczności OOOZ
# Copyright (C) 2026 semkishow
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

import asyncio, discord
from discord import app_commands

import database
from common import config, event_listener, log_exceptions, parse_duration
from features.utils import check_staff

# This is more accurate, than TextChannel.last_message_id for some reason, so we just use it.
async def _get_last_message(channel):
  return await anext(channel.history(limit=1))

async def _remove_last_sticky(channel):
  message_id = database.data.get('sticky_messages', {}).get(channel.id, {}).get('message_id', None)
  if message_id is None:
    return
  try:
    message = await channel.fetch_message(message_id)
    await message.delete()
  except discord.errors.NotFound:
    pass

lock = asyncio.Lock()

async def _update_sticky(channel):
  async with lock:
    channel_entry = database.data.setdefault('sticky_messages', {}).setdefault(channel.id, {})
    sticky_content = channel_entry['content']
    sticky_active = channel_entry['active']
    if sticky_content is None or not sticky_active:
      return
    new_sticky = await channel.send(sticky_content)
    await _remove_last_sticky(channel)
    database.data.setdefault('sticky_messages', {}).setdefault(channel.id, {})['message_id'] = new_sticky.id

message_tasks = []

@log_exceptions
async def _wait_for_message(message):
  channel_entry = database.data.setdefault('sticky_messages', {}).setdefault(message.channel.id, {})
  await asyncio.sleep(parse_duration(channel_entry['cooldown']))
  last_message_id = (await _get_last_message(message.channel)).id
  if last_message_id != message.id:
    return
  await asyncio.shield(_update_sticky(message.channel))

@event_listener
async def on_message(message):
  channel_entry = database.data.setdefault('sticky_messages', {}).setdefault(message.channel.id, {})
  sticky_active = channel_entry['active']
  if message.author == bot.user or message.guild is None or message.guild.id != config['guild'] or not sticky_active:
    return

  for task in message_tasks:
    task.cancel()
    try:
      await task
    except asyncio.CancelledError:
      pass
  message_tasks.clear()

  message_tasks.append(asyncio.create_task(_wait_for_message(message)))

sticky = app_commands.Group(name='sticky', description='Komendy do przypiętych wiadomości')

@sticky.command(name='set', description='Ustawia przypiętą wiadomość na aktualnym kanale')
@app_commands.rename(content='wiadomość')
@app_commands.describe(content='Treść przypiętej wiadomości')
@app_commands.describe(cooldown='Minimalny odstęp czasu pomiędzy kolejnymi wiadomościami')
@app_commands.choices(cooldown=[app_commands.Choice(name=label, value=duration) for label, duration in config['sticky_cooldown_choices']])
@check_staff('zmiany przypiętych wiadomości')
async def cmd_set(interaction, content: str, cooldown: str = config['sticky_default_cooldown']):
  log.info(f'Setting a new sticky message in channel {interaction.channel.id}')
  channel_entry = database.data.setdefault('sticky_messages', {}).setdefault(interaction.channel.id, {})
  channel_entry['content'] = content
  channel_entry['cooldown'] = cooldown
  channel_entry['active'] = True
  await _update_sticky(interaction.channel)
  await interaction.response.send_message(f'Pomyślnie ustawiono przypiętą wiadomość 🫡', ephemeral=True)

@sticky.command(name='set-cooldown', description='Ustawia minimalny odstęp czasu pomiędzy kolejnymi wiadomościami')
@app_commands.describe(cooldown='Minimalny odstęp czasu pomiędzy kolejnymi wiadomościami')
@app_commands.choices(cooldown=[app_commands.Choice(name=label, value=duration) for label, duration in config['sticky_cooldown_choices']])
@check_staff('zmiany przypiętych wiadomości')
async def cmd_set_cooldown(interaction, cooldown: str):
  log.info(f'Setting the sticky message cooldown in channel {interaction.channel.id}')
  database.data.setdefault('sticky_messages', {}).setdefault(interaction.channel.id, {})['cooldown'] = cooldown
  await interaction.response.send_message(f'Pomyślnie ustawiono cooldown na {cooldown} 🫡', ephemeral=True)

@sticky.command(name='pause', description='Zatrymuje wysyłanie przypiętej wiadomości')
@check_staff('zmiany przypiętych wiadomości')
async def cmd_pause(interaction):
  if not interaction.channel.id in database.data.setdefault('sticky_messages', {}):
    await interaction.response.send_message('Nie ma przypiętej wiadomości na tym kanale 🤨', ephemeral=True)
    return
  channel_entry = database.data.setdefault('sticky_messages', {}).setdefault(interaction.channel.id, {})
  if not channel_entry['active']:
    await interaction.response.send_message('Przypięta wiadomość już jest wyłączona na tym kanale 🤨', ephemeral=True)
    return
  log.info(f'Pausing the sticky message in channel {interaction.channel.id}')
  channel_entry['active'] = False
  await interaction.response.send_message('Pomyślnie zatrzymano wysyłanie przypiętej wiadomości 🫡', ephemeral=True)

@sticky.command(name='resume', description='Ponawia wysyłanie przypiętej wiadomości')
@check_staff('zmiany przypiętych wiadomości')
async def cmd_resume(interaction):
  log.info(f'Resuming the sticky message in channel {interaction.channel.id}')
  database.data.setdefault('sticky_messages', {}).setdefault(interaction.channel.id, {})['active'] = True
  await _update_sticky(interaction.channel)
  await interaction.response.send_message('Pomyślnie ponowiono wysyłanie przypiętej wiadomości 🫡', ephemeral=True)
