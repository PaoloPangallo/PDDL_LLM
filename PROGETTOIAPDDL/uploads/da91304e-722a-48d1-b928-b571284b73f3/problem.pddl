(define (problem varnaks-adventure)
     :domain swords-and-dragons
     :objects (agent hero) (location village cave dragon-cave) (hidden-item sword)
     :init
       (at hero village)
       (hidden sword cave)
       (asleep dragon dragon-cave)
     :goal (and (has hero sword) (not (asleep dragon dragon-cave)))
   )