from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .travel import TravelRequest, TravelSystem


class Provider(StrEnum):
    TRUST = "trust"
    SUPERWARP = "superwarp"
    NATIVE = "native"


@dataclass(slots=True, frozen=True)
class ProviderCommand:
    provider: Provider
    command: str
    description: str = ""


class SuperwarpProvider:
    """Command-level integration with AkadenTK/superwarp.

    XI Command deliberately does not vendor or reproduce Superwarp's menu logic.
    It emits documented addon commands to a separately-installed Superwarp.
    """

    _systems: dict[TravelSystem, str] = {
        TravelSystem.HOME_POINT: "hp",
        TravelSystem.WAYPOINT: "wp",
        TravelSystem.PROTO_WAYPOINT: "pwp",
        TravelSystem.SURVIVAL_GUIDE: "sg",
        TravelSystem.ESCHA: "ew",
        TravelSystem.UNITY: "un",
        TravelSystem.ABYSSEA: "ab",
        TravelSystem.RUNIC_PORTAL: "po",
        TravelSystem.VOIDWATCH: "vw",
        TravelSystem.SORTIE: "so",
        TravelSystem.ODYSSEY: "od",
        TravelSystem.LIMBUS: "li",
    }

    def command_for(self, request: TravelRequest, *, scope: str = "all") -> ProviderCommand:
        token = self._systems[request.system]
        scope_token = scope.casefold()
        if scope_token not in {"all", "party", "local"}:
            raise ValueError("Superwarp scope must be all, party, or local")

        parts = ["sw", token]
        if scope_token != "local":
            parts.append(scope_token)
        parts.append(_quote_if_needed(request.destination))
        if request.sub_destination:
            parts.append(_quote_if_needed(request.sub_destination))

        return ProviderCommand(
            Provider.SUPERWARP,
            " ".join(parts),
            f"Travel via Superwarp: {request.system.value} {request.destination}",
        )

    def cancel(self, *, scope: str = "all") -> ProviderCommand:
        if scope not in {"all", "party", "local"}:
            raise ValueError("Superwarp scope must be all, party, or local")
        suffix = "" if scope == "local" else f" {scope}"
        return ProviderCommand(Provider.SUPERWARP, f"sw cancel{suffix}", "Cancel active Superwarp travel")


@dataclass(slots=True, frozen=True)
class TrustProfile:
    main_character: str
    follow_distance: float = 3.0
    engage_mode: str = "Mirror"
    skillchain_mode: str = "Auto"
    magic_burst_mode: str = "Auto"
    restore_mana_mode: str = "Auto"
    pulling_enabled: bool = False


class TrustProvider:
    """Command-level integration with cyritegamestudios/trust.

    Trust is an external dependency. Its license currently prohibits redistribution,
    forks and derivative works without written permission, so XI Command only uses
    documented public commands and never vendors Trust source.
    """

    def bootstrap_multibox(self, profile: TrustProfile) -> list[ProviderCommand]:
        main = _safe_name(profile.main_character)
        commands = [
            ProviderCommand(Provider.TRUST, "trust startall", "Enable Trust on local characters"),
            ProviderCommand(Provider.TRUST, "trust assist me", f"Make party assist {main}"),
            ProviderCommand(Provider.TRUST, "trust follow me", f"Make party follow {main}"),
            self._sendall_set("AutoFollowMode", "Always"),
            self._sendall_set("AutoEngageMode", profile.engage_mode),
            self._sendall_set("AutoSkillchainMode", profile.skillchain_mode),
            self._sendall_set("AutoMagicBurstMode", profile.magic_burst_mode),
            self._sendall_set("AutoRestoreManaMode", profile.restore_mana_mode),
            self._sendall_set("AutoPullMode", "Auto" if profile.pulling_enabled else "Off"),
            ProviderCommand(
                Provider.TRUST,
                f"trust sendall trust follow distance {profile.follow_distance:g}",
                "Set alt follow distance",
            ),
        ]
        return commands

    def combat_safe_mode(self) -> list[ProviderCommand]:
        """Disable behaviors that can acquire/pull targets independently."""
        return [
            self._sendall_set("AutoPullMode", "Off"),
            self._sendall_set("AutoEngageMode", "Mirror"),
        ]

    def stop_all(self) -> ProviderCommand:
        return ProviderCommand(Provider.TRUST, "trust stopall", "Disable Trust automation on other clients")

    def follow(self, character: str = "me") -> ProviderCommand:
        if character.casefold() == "me":
            return ProviderCommand(Provider.TRUST, "trust follow me", "Make local party follow this character")
        return ProviderCommand(Provider.TRUST, f"trust follow {_safe_name(character)}", f"Follow {character}")

    def stop_follow(self) -> ProviderCommand:
        return ProviderCommand(Provider.TRUST, "trust follow stopall", "Stop follow on local party")

    @staticmethod
    def _sendall_set(mode: str, value: str) -> ProviderCommand:
        return ProviderCommand(
            Provider.TRUST,
            f"trust sendall trust set {mode} {value}",
            f"Set {mode}={value} on all Trust clients",
        )


@dataclass(slots=True, frozen=True)
class RestPolicy:
    start_mp_percent: int = 20
    stop_mp_percent: int = 80
    minimum_idle_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not 0 <= self.start_mp_percent < self.stop_mp_percent <= 100:
            raise ValueError("rest thresholds must satisfy 0 <= start < stop <= 100")
        if self.minimum_idle_seconds < 0:
            raise ValueError("minimum_idle_seconds must be non-negative")


class NativeRestProvider:
    """Small XI Command-owned gap filler for classic /heal resting.

    The state machine intentionally does not decide what to fight or move to a camp.
    It only rests an already-idle, disengaged character between authorized fights.
    """

    def __init__(self, policy: RestPolicy | None = None) -> None:
        self.policy = policy or RestPolicy()

    def desired_action(
        self,
        *,
        mp_percent: int,
        engaged: bool,
        casting: bool,
        currently_resting: bool,
        idle_seconds: float,
    ) -> ProviderCommand | None:
        if engaged or casting:
            if currently_resting:
                return ProviderCommand(Provider.NATIVE, "input /heal off", "Stand up for combat/action")
            return None

        if currently_resting:
            if mp_percent >= self.policy.stop_mp_percent:
                return ProviderCommand(Provider.NATIVE, "input /heal off", "MP rest target reached")
            return None

        if mp_percent <= self.policy.start_mp_percent and idle_seconds >= self.policy.minimum_idle_seconds:
            return ProviderCommand(Provider.NATIVE, "input /heal on", "Rest to recover MP")
        return None


def _safe_name(value: str) -> str:
    if not value or not value.replace("-", "").replace("'", "").isalnum():
        raise ValueError(f"invalid character name: {value!r}")
    return value


def _quote_if_needed(value: str) -> str:
    value = str(value)
    if not value:
        return '""'
    if any(ch.isspace() for ch in value) or "'" in value or '"' in value:
        return '"' + value.replace('"', '\\"') + '"'
    return value
