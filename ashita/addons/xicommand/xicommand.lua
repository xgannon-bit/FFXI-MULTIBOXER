addon.name = 'xicommand';
addon.author = 'FFXI-MULTIBOXER';
addon.version = '0.1.0';
addon.desc = 'Attended multibox orchestration agent for XI Command.';
addon.link = 'https://github.com/xgannon-bit/FFXI-MULTIBOXER';

require 'common';

local chat = require 'chat';

local state = {
    armed = false,
    travel_active = false,
    last_travel = nil,
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

local function show_status()
    info(('Agent v%s | Character: %s | Encounter: %s | Travel: %s'):format(
        addon.version,
        get_character_name(),
        state.armed and 'ARMED' or 'DISARMED',
        state.travel_active and 'ACTIVE' or 'idle'
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
        error_msg('A travel operation is already active. Use /xmb cancel first.');
        return;
    end

    state.last_travel = {
        system = system,
        destination = destination,
        sub_destination = sub_destination or '',
    };

    -- M0 intentionally uses a visible dry-run provider. This proves the Ashita
    -- parser/state machine before we enable CatsEye menu execution. The next
    -- provider will replace this with Home Point / Survival Guide menu drivers.
    state.travel_active = true;
    info(('TRAVEL DRY RUN -> %s | %s | %s'):format(system, destination, sub_destination or ''));
    state.travel_active = false;
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

    if (cmd == 'travel') then
        -- Local test syntax:
        -- /xmb travel hp "Ru\'Lude Gardens" 1
        -- Controller scope (all/party/character) lives in the desktop app; each
        -- agent receives a character-specific resolved command.
        local system = args[3];
        local destination = args[4];
        local sub_destination = args[5];
        if (system == nil or destination == nil) then
            error_msg('Usage: /xmb travel <system> <destination> [sub_destination]');
            return true;
        end
        begin_travel(system:lower(), destination, sub_destination);
        return true;
    end

    if (cmd == 'help') then
        info('/xmb status | arm | disarm | cancel');
        info('/xmb travel <hp|wp|pwp|sg|ew|un|ab|po|vw|so|od|li> <destination> [sub]');
        return true;
    end

    error_msg('Unknown command. Use /xmb help.');
    return true;
end

ashita.events.register('load', 'xicommand_load', function ()
    info(('v%s loaded. Use /xmb status.'):format(addon.version));
end);

ashita.events.register('unload', 'xicommand_unload', function ()
    state.armed = false;
    state.travel_active = false;
end);

ashita.events.register('command', 'xicommand_command', function (e)
    if (handle_command(e.command)) then
        e.blocked = true;
    end
end);
