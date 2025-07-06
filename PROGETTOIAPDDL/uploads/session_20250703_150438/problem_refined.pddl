(define (problem quest-title)
  (:domain world-context)
  (:objects 
    hero - hero 
    sword-of-fire - sword 
    tower-of-varnak - tower 
    ice-dragon - dragon 
    village - village 
    ground - ground 
  )
  (:init 
    (at hero village) 
    (on-ground sword-of-fire ground) 
    (sleeping ice-dragon) 
    (at ice-dragon ground)
  )
  (:goal 
    (and (at hero tower-of-varnak) 
         (carrying hero sword-of-fire) 
         (defeated ice-dragon)))
)