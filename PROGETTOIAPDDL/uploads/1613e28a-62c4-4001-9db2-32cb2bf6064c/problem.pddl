(define (problem la-spada-di-varnak)
     (domain la-spada-di-varnak)
     :objects (hero dragon - agent) (sword cave)
     :init
       (and (at hero village) (hidden sword cave) (sleeping dragon))
     :goal
       (and (has hero sword) (defeated dragon))
   )