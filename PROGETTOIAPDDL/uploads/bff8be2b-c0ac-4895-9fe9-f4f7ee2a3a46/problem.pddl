(define p0
     (:domain la-spada-di-varnak
      :objects hero cave dragon sword
      :init (and (at hero village) (sleeping dragon) (sword-in cave))
      :goal (and (has hero sword) (defeated dragon))
      :state-variables (at hero location)
                       (has hero sword)
                       (sleeping dragon)
                       (sword-in cave)
                       (sword-in hand))
   )