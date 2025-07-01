(define (problem tower-of-varnak-problem)
    :domain tower-of-varnak
    :objects
      (hero dragon sword)
    :init
      (and
        (at hero village)
        (on-ground sword-of-fire tower-of-varnak)
        (sleeping dragon)
        (inventory-item hero sword))
    :goal (and (at hero tower-of-varnak) (awake dragon) (carrying hero sword)))