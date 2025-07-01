(:domain quest_adventure
    (:objects hero tower-of-varnak sword-of-fire ice-dragon village))
   (:init
    (at hero village)
    (on-ground sword-of-fire tower-of-varnak)
    (sleeping ice-dragon))
   (:goal (and (at hero tower-of-varnak) (awake ice-dragon)))