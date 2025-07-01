(define (domain tower-of-varnak)
      :requirements ((linear))
      :types agent location monster object
      :predicates
        (at ?a ?loc)
        (on-ground ?o ?loc)
        (carrying ?a ?o)
        (sleeping ?m)
        (awake ?m)
      :actions
        (move
          :parameters (?a ?loc1 ?loc2)
          :precondition (and (at ?a ?loc1) (not (on-ground ?a ?loc1)))
          :effect (and (at ?a ?loc2) (not (at ?a ?loc1)) (not (on-ground ?a ?loc1))))
        (pickup
          :parameters (?a ?o ?loc)
          :precondition (and (and (on-ground ?o ?loc) (at ?a ?loc)) (not (carrying ?a ?o)))
          :effect (and (not (on-ground ?o ?loc)) (carrying ?a ?o))))
   (:type location (village tower-of-varnak))
   (:function location-north ?loc -1)
   (:function location-east ?loc 1)
   (:function location-west ?loc -1)
   (:function location-south ?loc 1)
   (:type monster (sleeping awake))
   (:function sleeping-awake ?m 0)
   (:action wake-dragon
     :parameters (?m)
     :precondition (and (sleeping ?m))
     :effect (and (not (sleeping ?m)) (awake ?m)))