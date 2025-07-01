(define (domain tower-of-varnak)
       :requirements ((linear))
       :types agent location dragon sword
       :predicates
         (at ?a ?loc)
         (on-ground ?s ?loc)
         (carrying ?a ?s)
         (sleeping ?d)
         (awake ?d)
       :actions
         (move
           :parameters (?a ?loc1 ?loc2)
           :precondition (and (at ?a ?loc1) (not (on-ground ?a ?loc1)))
           :effect (and (at ?a ?loc2) (not (at ?a ?loc1)) (not (on-ground ?a ?loc1))))
         (pickup
           :parameters (?a ?s ?loc)
           :precondition (and (and (on-ground ?s ?loc) (at ?a ?loc)) (not (carrying ?a ?s)))
           :effect (and (not (on-ground ?s ?loc)) (carrying ?a ?s))))
   (:type location (city tower))
   (:function location-north ?loc -1)
   (:function location-east ?loc 1)
   (:function location-west ?loc -1)
   (:function location-south ?loc 1)
   (:type dragon (sleeping awake))
   (:function sleeping-awake ?d 0)
   (:action wake-dragon
     :parameters (?d)
     :precondition (and (sleeping ?d))
     :effect (and (not (sleeping ?d)) (awake ?d)))