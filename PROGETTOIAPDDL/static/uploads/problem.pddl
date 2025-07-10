(define (problem hero-adventure-problem)
  (:domain hero-adventure)

  (:objects 
    ; Define the objects in the problem
    hero - agent
    tower-of-varnak - location
    sword-of-fire - object
    ice-dragon - monster
    village - location)

  (:init 
    ; Initialize the state of the world
    (and (at hero village)
         (on-ground sword-of-fire tower-of-varnak)
         (sleeping ice-dragon)))

  (:goal 
    ; Define the goal conditions
    (and (at hero tower-of-varnak)
         (carrying hero sword-of-fire)
         (defeated ice-dragon)))
)