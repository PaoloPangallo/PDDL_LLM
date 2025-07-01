(define (domain tower-of-varnak)
       :requirements ((linear-time))
       :types agent location mountain dragon_status sword
       :predicates
         (at ?a ?loc)
         (on-ground ?s ?o)
         (carrying ?a ?s)
         (sleeping ?d)
         (awake ?d)
         (defeated ?d)
       :action
         (move
           :parameters (?a ?to-loc)
           :precondition (and (at ?a ?loc) (not (= ?to-loc mountain)))
           :effect (and (not (at ?a ?loc)) (at ?a ?to-loc)))
         (pickup
           :parameters (?a ?o)
           :precondition (and (on-ground ?o ?location) (at ?a location))
           :effect (and (not (on-ground ?o ?location)) (carrying ?a ?o)))
         (putdown
           :parameters (?a ?o)
           :precondition (and (carrying ?a ?o) (at ?a location))
           :effect (and (not (carrying ?a ?o)) (on-ground ?o ?location)))
         (defeat
           :parameters (?a ?d)
           :precondition (and (carrying ?a sword) (at ?a mountain) (awake ?d))
           :effect (and (not (sleeping ?d)) (defeated ?d)))
         (wake_dragon
           :parameters ()
           :precondition (and (at hero mountain) (defeated ice-dragon))
           :effect (awake ice-dragon))
         (rest
           :parameters ()
           :precondition (and (at hero village))
           :effect (sleeping ice-dragon))
     :objects
       (hero villager mountain sword dragon)  ; Added 'villager' and removed 'ice-dragon' from the list, assuming it should be an object in the problem too.