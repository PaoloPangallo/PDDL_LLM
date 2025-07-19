(define (problem RetrieveEmerald)
  (:domain ElvenRealm)
  (:objects
    Arin                  - agent
    PortMurias
    SunlitCliffs
    ShadowedMarsh
    TempleOfTides         - location
    CoralLockpick
    GlassLantern
    EmeraldOfDawn         - item
    LivingStoneGolems     - monster
  )
  (:init
    (at Arin PortMurias)
    (can_move PortMurias SunlitCliffs)
    (can_move SunlitCliffs PortMurias)
    (can_move PortMurias ShadowedMarsh)
    (can_move ShadowedMarsh PortMurias)
    (can_move SunlitCliffs TempleOfTides)
    (can_move TempleOfTides SunlitCliffs)
    (can_move ShadowedMarsh TempleOfTides)
    (can_move TempleOfTides ShadowedMarsh)
    (is_dangerous SunlitCliffs)
    (item_at GlassLantern ShadowedMarsh)
    (item_at EmeraldOfDawn TempleOfTides)
    (has Arin CoralLockpick)
  )
  (:goal
    (and
      (at Arin PortMurias)
      (has Arin EmeraldOfDawn)
      (defeated LivingStoneGolems)
    )
  )
)