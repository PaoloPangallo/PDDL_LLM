(define (domain adventure-domain)
  (:requirements strips)

  (:types none)

  (:predicates 
    (at ?agent - agent ?location)  
    (carrying ?agent ?item)        
    (sleeping ?dragon)
    (at ?agent ?location)  
    (on-ground ?item ?location)  
    (sleeping ?dragon)  
    (not ?bool))

  (:action move-to-destination
    :parameters (?from - location ?to - location)
    :precondition (and (not (= ?from ?to)) (at hero ?from))
    :effect (not (at hero ?from)) (at hero ?to)

  (:action pick-up-sword
    :parameters ()
    :precondition (and (on-ground sword-of-fire tower-of-varnak) (at hero tower-of-varnak))
    :effect (carrying hero sword-of-fire))

  (:action defeat-dragon
    :parameters ()
    :precondition (and (sleeping ice-dragon) (at hero tower-of-varnak) (carrying hero sword-of-fire))
    :effect (not (sleeping ice-dragon)))