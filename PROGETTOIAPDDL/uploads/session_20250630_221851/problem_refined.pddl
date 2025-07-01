
(define (problem tower-of-varnak-problem)
  :domain tower-of-varnak
  :objects
    (hero dragon sword) ;; Added "dragon" object to reflect the ice-dragon mentioned in the validation report
  :init
    (and
      (at hero village)
      (on-ground sword tower-of-varnak)
      (sleeping dragon)
      (inventory-item hero sword)) ;; Updated inventory-item initialization for the hero and sword
  :goal (and (at hero tower-of-varnak) (awake dragon) (carrying hero sword)))
```