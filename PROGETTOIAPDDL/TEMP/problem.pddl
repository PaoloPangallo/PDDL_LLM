(define (problem tower-of-varnak-problem)
      :domain tower-of-varnak
      :objects
        (hero village hero-sword tower-of-varnak ice-dragon)
      :init
        (and
          (at hero village)
          (on-ground sword-of-fire tower-of-varnak)
          (sleeping ice-dragon))
      :goal (and (at hero tower-of-varnak) (awake ice-dragon) (carrying hero sword-of-fire)))