(define (problem tower-of-varnak)
  (:domain world)
  (:objects 
    hero 
    sword-of-fire 
    tower-of-varnak 
    ice-dragon 
    village 
    ground 
    ice 
    fire)
  (:init 
    (at hero village)
    (on-ground sword-of-fire ground)
    (on-ground tower-of-varnak ground)
    (sleeping ice-dragon ground)
    (carrying hero sword-of-fire))
  (:goal 
    (and (at hero tower-of-varnak) (not (sleeping ice-dragon ground)))))