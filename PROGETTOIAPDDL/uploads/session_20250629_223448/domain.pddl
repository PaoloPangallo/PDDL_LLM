(define (domain hero-adventure)
     :requirements ((equal (world-size) small)
                    (equal (has-sword hero) true)
                    (not (dead hero)))
     :types agent location object
     :predicates
       (at agent location)
       (on-ground object location)
       (sleeping object)
       (awake object)
       (carrying agent object)
       (has-item agent object)
     :action take
       :parameters (?agent ?location ?obj)
       :precondition (and (at ?agent ?location) (on-ground ?obj ?location))
       :effect (and (not (on-ground ?obj ?location)) (carrying ?agent ?obj))
     :action drop
       :parameters (?agent ?obj)
       :precondition (carrying ?agent ?obj)
       :effect (and (on-ground ?obj (location ?agent)) (not (carrying ?agent ?obj)))
     :action move-to
       :parameters (?agent ?new-location)
       :precondition (at ?agent (location ?new-location))
       :effect (at ?agent ?new-location)
     :action wake-up
       :parameters (?dragon)
       :precondition (sleeping ?dragon)
       :effect (awake ?dragon)
     :action defeat-dragon
       :parameters (?hero ?dragon)
       :precondition (and (at ?hero (location ?dragon)) (carrying sword-of-fire) (awake ?dragon))
       :effect (not (alive ?dragon)))