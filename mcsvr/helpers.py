import ipaddress
import logging
import socket
from typing import Union

import discord
import validators
from mcstatus import MinecraftServer

log = logging.getLogger("red.mcsvr")

MC_FORMATTING_CODES = [
    "§0",
    "§1",
    "§2",
    "§3",
    "§4",
    "§5",
    "§6",
    "§7",
    "§8",
    "§9",
    "§a",
    "§b",
    "§c",
    "§d",
    "§e",
    "§f",
    "§k",
    "§l",
    "§m",
    "§n",
    "§o",
    "§r",
]


def is_valid_ip(addr: str):
    addr = addr.split(":")
    port = None
    if len(addr) > 1:
        port = int(addr[1])
    addr = addr[0]
    try:
        ipaddress.ip_address(addr)
    except ValueError:
        if not validators.domain(addr):
            return False
    if port is not None and port not in range(0, 65535):
        return False
    return True

@DeprecationWarning
def check_server(addr: str) -> Union[discord.Embed, str, None]:
    # Deprecated in favor of using async_status vs status. async_query is not implemented yet
    mc_server = MinecraftServer.lookup(addr)

    query = None
    status = None

    try:
        query = mc_server.query()
    except socket.timeout:
        try:
            status = mc_server.status()
        except socket.timeout:
            log.warning("Cannot reach server {}".format(addr))
        except ConnectionRefusedError:
            log.warning("Connection to {} was refused".format(addr))
        except OSError:
            log.warning("No route to {}".format(addr))
            return None
    except ConnectionRefusedError:
        log.warning("Connection to {} was refused".format(addr))
    except OSError:
        log.warning("No route to {}".format(addr))
        return None
    if query:
        return query
    elif status:
        return status
    else:
        return None


def get_server_string(mc_server, server_ip):
    if mc_server is None:
        data = "Server info for {}:\n\n".format(server_ip)
        data += "Online: No"
        return data
    else:
        players = None
        brand = None
        motd = None
        if hasattr(mc_server, "software"):
            players = mc_server.players.names
            version = mc_server.software.version
            brand = mc_server.software.brand
            motd = mc_server.motd
        else:
            version = mc_server.version.name
        online_count = mc_server.players.online
        max_count = mc_server.players.max
        data = "Server info for {}:\n\n".format(server_ip)
        data += "Online: Yes\n"
        data += "Online count: {}/{}\n".format(online_count, max_count)
        if players:
            s = "Players online: {}\n"
            if len(players) > 5:
                s.format(", ".join(players[:5]) + " and {} more".format(len(players[5:])))
            else:
                s.format(", ".join(players))
            data += s
        data += "Version: {}\n".format(version)
        if brand:
            data += "Type: {}\n".format(brand)
        if motd:
            for code in MC_FORMATTING_CODES:
                if code in motd:
                    motd = motd.replace(code, "")
            data += "MOTD: {}\n".format(motd)
        return data.strip()


def get_server_embed(mc_server, server_ip):
    if mc_server is None:
        emb = discord.Embed(title="Server info for {}".format(server_ip))
        emb.add_field(name="Online", value="No")
        return emb
    else:
        players = None
        brand = None
        motd = None
        if hasattr(mc_server, "software"):
            players = mc_server.players.names
            version = mc_server.software.version
            brand = mc_server.software.brand
            motd = mc_server.motd
        else:
            version = mc_server.version.name
        online_count = mc_server.players.online
        max_count = mc_server.players.max
        emb = discord.Embed(title="Server info for {}".format(server_ip))
        emb.add_field(name="Online", value="Yes")
        emb.add_field(name="Online count", value="{}/{}".format(online_count, max_count))
        if players:
            emb.set_footer(text="Players online: {}".format(", ".join(players)))
        emb.add_field(name="Version", value=version)
        if brand:
            emb.add_field(name="Type", value=brand)
        if motd:
            for code in MC_FORMATTING_CODES:
                if code in motd:
                    motd = motd.replace(code, "")
            emb.add_field(name="MOTD", value=motd)

        return emb
