(:domain tower-quest)
  (:objects
    (hero)
    (tower-of-varnak)
    (sword-of-fire)
    (ice-dragon))

  (:init
    (at hero village)
    (on-ground sword-of-fire tower-of-varnak)
    (sleeping ice-dragon)
    (carrying hero sword-of-fire))

  (:goal (and (at hero tower-of-varnak) (awake ice-dragon) (not (exists ice-dragon (sleeping ice-dragon)))))