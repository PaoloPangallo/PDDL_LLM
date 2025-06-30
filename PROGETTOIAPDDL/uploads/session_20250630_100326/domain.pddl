(define (domain hero-adventure)
     :requirements ((eql (language -) lisp))
     :types agent location object
     :predicates
       (at ?a ?loc)
       (on-ground ?o ?loc)
       (holding ?h ?o)
       (sleeping ?d)
       (awake ?d)
     :action
       (move
         :parameters (?a ?loc1 ?loc2)
         :precondition (and (at ?a ?loc1) (not (= ?loc1 ?loc2)))
         :effect (and (not (at ?a ?loc1)) (at ?a ?loc2) (not (= ?loc1 ?loc2))))
       (pickup
         :parameters (?a ?o ?loc)
         :precondition (and (at ?a ?loc) (on-ground ?o ?loc) (not (holding ?a ?o)))
         :effect (and (not (on-ground ?o ?loc)) (holding ?a ?o)))
       (putdown
         :parameters (?a ?o ?loc)
         :precondition (and (at ?a ?loc) (holding ?a ?o))
         :effect (and (on-ground ?o ?loc) (not (holding ?a ?o))))
       (wakeup
         :parameters (?d)
         :precondition (and (sleeping ?d))
         :effect (awake ?d)))