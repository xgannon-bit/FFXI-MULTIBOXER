addon.name = 'xicommand';
addon.author = 'FFXI-MULTIBOXER';
addon.version = '0.2.0';
addon.desc = 'Attended multibox orchestration agent for XI Command.';
addon.link = 'https://github.com/xgannon-bit/FFXI-MULTIBOXER';

require 'common';

local chat = require 'chat';
local socket = require 'socket';

local PROTOCOL_VERSION = '1';
local CONTROLLER_HOST = '127.0.0.1';
local CONTROLLER_PORT = 19775;
local HEARTBEAT_SECONDS = 2.0;

local state = {
    armed = false,
    travel_active = false,
    last_travel = nil,
    udp = nil,
    transport_online = false,
    last_heartbeat = 0,
    last_hello_name = nil,
    rx_count = 0,
    tx_count = 0,
};

local function header()
    return chat.header('XI Command');
end

local function info(message)
    print(header():append(chat.message(message)));
end

local function error_msg(message)
    print(header():append(chat.error(message)));
end

local function escape_field(value)
    value = tostring(value or '');
    value = value:gsub('\\', '\\\\');
    value = value:gsub('|', '\\p');
    value = value:gsub('\n', '\\n');
    return value;
end

local function split_escaped(line)
    local out = {};
    local buf = {};
    local escaped = false;
    local i = 1;
    while (i <= #line) do
        local ch = line:sub(i, i);
        if (escaped) then
            if (ch == 'p') then
                buf[#buf + 1] = '|';
            elseif (ch == 'n') then
                buf[#buf + 1] = '\n';
            else
                buf[#buf + 1] = ch;
            end
            escaped = false;
        elseif (ch == '\\') then
            escaped = true;
        elseif (ch == '|') then
            out[#out + 1] = table.concat(buf);
            buf = {};
        else
            buf[#buf + 1] = ch;
        end
        i = i + 1;
    end
    if (escaped) then
        buf[#buf + 1] = '\\';
    end
    out[#out + 1] = table.concat(buf);
    return out;
end

local function encode_message(kind, fields)
    local parts = { PROTOCOL_VERSION, kind };
    for _, value in ipairs(fields or {}) do
        parts[#parts + 1] = escape_field(value);
    end
    return table.concat(parts, '|') .. '\n';
end

local function get_character_name()
    local party = AshitaCore:GetMemoryManager():GetParty();
    if (party == nil) then
        return 'Unknown';
    end
    local name = party:GetMemberName(0);
    if (name == nil or name == '') then
        return 'Unknown';
    end
    return name;
end

local function transport_send(kind, fields)
    if (state.udp == nil) then
        return false;
    end
    local payload = encode_message(kind, fields);
    local ok, err = state.udp:send(payload);
    if (not ok) then
        state.transport_online = false;
        return false, err;
    end
    state.tx_count = state.tx_count + 1;
    state.transport_online = true;
    return true;
end

local function send_hello(force)
    local name = get_character_name();
    if (name == 'Unknown') then
        return;
    end
    if ((not force) and state.last_hello_name == name) then
        return;
    end
    if (transport_send('HELLO', { name, addon.version, '' })) then
        state.last_hello_name = name;
    end
end

local function send_heartbeat()
    local name = get_character_name();
    if (name ~= 'Unknown') then
        transport_send('HEARTBEAT', { name, '' });
    end
end

local function send_ack(command_id, status, detail)
    transport_send('ACK', { command_id, get_character_name(), status, detail or '' });
end

local function tokenize(input)
    local args = {};
    local current = {};
    local quoted = false;
    local quote_char = nil;
    local i = 1;

    while (i <= #input) do
        local ch = input:sub(i, i);
        if (quoted) then
            if (ch == quote_char) then
                quoted = false;
                quote_char = nil;
            elseif (ch == '\\' and i < #input) then
                i = i + 1;
                current[#current + 1] = input:sub(i, i);
            else
                current[#current + 1] = ch;
            end
        else
            if (ch == '"' or ch == "'") then
                quoted = true;
                quote_char = ch;
            elseif (ch:match('%s')) then
                if (#current > 0) then
                    args[#args + 1] = table.concat(current);
                    current = {};
                end
            else
                current[#current + 1] = ch;
            end
        end
        i = i + 1;
    end

    if (#current > 0) then
        args[#args + 1] = table.concat(current);
    end
    return args;
end

local function show_status()
    info(('Agent v%s | Character: %s | Encounter: %s | Travel: %s | Controller: %s | tx=%d rx=%d'):format(
        addon.version,
        get_character_name(),
        state.armed and 'ARMED' or 'DISARMED',
        state.travel_active and 'ACTIVE' or 'idle',
        state.transport_online and 'online' or 'waiting',
        state.tx_count,
        state.rx_count
    ));
    if (state.last_travel ~= nil) then
        info(('Last travel request: %s %s %s'):format(
            state.last_travel.system,
            state.last_travel.destination,
            state.last_travel.sub_destination or ''
        ));
    end
end

local function begin_travel(system, destination, sub_destination)
    if (state.travel_active) then
        return false, 'travel already active';
    end

    state.last_travel = {
        system = system,
        destination = destination,
        sub_destination = sub_destination or '',
    };

    -- Transport is live in v0.2. Travel execution remains a visible dry-run
    -- provider until CatsEye menu flows are implemented and validated.
    state.travel_active = true;
    info(('TRAVEL DRY RUN -> %s | %s | %s'):format(system, destination, sub_destination or ''));
    state.travel_active = false;
    return true, 'dry-run accepted';
end

local function handle_controller_command(fields)
    -- CMD fields: command_id, scope, recipient, action, arg1...
    if (#fields < 4) then
        return;
    end
    local command_id = fields[1];
    local recipient = fields[3];
    local action = fields[4]:upper();
    local me = get_character_name();
    if (recipient ~= '*' and recipient:lower() ~= me:lower()) then
        return;
    end

    if (action == 'TRAVEL') then
        local system = fields[5] or '';
        local destination = fields[6] or '';
        local sub_destination = fields[7] or '';
        local ok, detail = begin_travel(system, destination, sub_destination);
        send_ack(command_id, ok and 'OK' or 'FAILED', detail);
        return;
    end

    if (action == 'PING') then
        send_ack(command_id, 'OK', 'pong');
        return;
    end

    send_ack(command_id, 'UNSUPPORTED', 'action not implemented in agent v0.2');
end

local function poll_controller()
    if (state.udp == nil) then
        return;
    end
    for _ = 1, 32 do
        local line, err = state.udp:receive();
        if (line == nil) then
            if (err ~= 'timeout') then
                state.transport_online = false;
            end
            break;
        end
        state.rx_count = state.rx_count + 1;
        state.transport_online = true;
        local parts = split_escaped(line);
        if (#parts >= 2 and parts[1] == PROTOCOL_VERSION) then
            local kind = parts[2];
            local fields = {};
            for i = 3, #parts do
                fields[#fields + 1] = parts[i];
            end
            if (kind == 'CMD') then
                handle_controller_command(fields);
            end
        end
    end
end

local function init_transport()
    if (state.udp ~= nil) then
        pcall(function () state.udp:close(); end);
        state.udp = nil;
    end
    local udp, err = socket.udp();
    if (udp == nil) then
        error_msg('Unable to create UDP socket: ' .. tostring(err));
        return false;
    end
    udp:settimeout(0);
    local ok, peer_err = udp:setpeername(CONTROLLER_HOST, CONTROLLER_PORT);
    if (not ok) then
        error_msg('Unable to connect UDP transport: ' .. tostring(peer_err));
        udp:close();
        return false;
    end
    state.udp = udp;
    state.transport_online = false;
    state.last_heartbeat = socket.gettime();
    send_hello(true);
    return true;
end

local function handle_command(raw)
    local args = tokenize(raw);
    if (#args == 0) then return false; end

    local root = args[1]:lower();
    if (root ~= '/xmb' and root ~= '/xicommand') then
        return false;
    end

    local cmd = (args[2] or 'status'):lower();
    if (cmd == 'status') then
        show_status();
        return true;
    end

    if (cmd == 'arm') then
        state.armed = true;
        info('Encounter orchestration ARMED by user input.');
        return true;
    end

    if (cmd == 'disarm') then
        state.armed = false;
        info('Encounter orchestration DISARMED.');
        return true;
    end

    if (cmd == 'cancel') then
        state.travel_active = false;
        info('Current travel operation cancelled.');
        return true;
    end

    if (cmd == 'reconnect') then
        init_transport();
        info('Controller transport reconnect requested.');
        return true;
    end

    if (cmd == 'ping') then
        send_hello(true);
        transport_send('EVENT', { get_character_name(), 'LOCAL_PING', tostring(socket.gettime()) });
        info('Controller ping/hello sent.');
        return true;
    end

    if (cmd == 'travel') then
        local system = args[3];
        local destination = args[4];
        local sub_destination = args[5];
        if (system == nil or destination == nil) then
            error_msg('Usage: /xmb travel <system> <destination> [sub_destination]');
            return true;
        end
        local ok, detail = begin_travel(system:lower(), destination, sub_destination);
        if (not ok) then error_msg(detail); end
        return true;
    end

    if (cmd == 'help') then
        info('/xmb status | arm | disarm | cancel | reconnect | ping');
        info('/xmb travel <hp|wp|pwp|sg|ew|un|ab|po|vw|so|od|li> <destination> [sub]');
        return true;
    end

    error_msg('Unknown command. Use /xmb help.');
    return true;
end

ashita.events.register('load', 'xicommand_load', function ()
    init_transport();
    info(('v%s loaded. Use /xmb status.'):format(addon.version));
end);

ashita.events.register('unload', 'xicommand_unload', function ()
    state.armed = false;
    state.travel_active = false;
    if (state.udp ~= nil) then
        pcall(function () state.udp:close(); end);
        state.udp = nil;
    end
end);

ashita.events.register('command', 'xicommand_command', function (e)
    if (handle_command(e.command)) then
        e.blocked = true;
    end
end);

ashita.events.register('d3d_present', 'xicommand_transport_tick', function ()
    poll_controller();
    local now = socket.gettime();
    if ((now - state.last_heartbeat) >= HEARTBEAT_SECONDS) then
        send_hello(false);
        send_heartbeat();
        state.last_heartbeat = now;
    end
end);
