(define (problem tower-of-varnak)
       :domain tower-of-varnak
       :objects (hero villager mountain sword ice-dragon)
       :init
         (and (at hero village) (on-ground sword mountain) (sleeping ice-dragon) (awake villager))  ; Added 'villager' and changed the state of 'ice-dragon' to 'asleep'. Also added 'awake villager' assuming it is necessary for some action.
       :goal (and (at hero mountain) (defeated ice-dragon)))