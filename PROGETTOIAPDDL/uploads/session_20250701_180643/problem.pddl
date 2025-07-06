(define (problem puzzle-problem)
  (:domain puzzle)
  (:objects
    box1 - box
    box2 - box
    key1 - key
    key2 - key
    door1 - door
    room1 - room
    room2 - room
    sword-of-fire - sword
    tower-of-varnak - tower
    ice-dragon - dragon
    hero - hero
    village - village
  )
  (:init
    (at hero village)
    (at box1 room1)
    (at key1 room2)
    (at door1 room2)
    (on-ground sword-of-fire tower-of-varnak)
    (sleeping ice-dragon)
  )
  (:goal
    (and (at hero room1) (at box1 room2) (at key1 room1) (at door1 room1) (at sword-of-fire room1) (at ice-dragon room1))
  )
)