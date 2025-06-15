(define problem swords-in-the-cave
     (:domain swords-and-dragons
       :objects (hero dragon cave sword village)
       :init (and (at hero village) (hidden sword cave) (sleeping-dragon))
       :goal (and (has hero sword) (defeated dragon)))
   )