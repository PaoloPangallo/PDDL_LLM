(define domain swords-and-dragons
     (:requirements regular
       common-sense
       equality)

     (:types agent location action agent action result)
     (:predicates
      (at ?a ?l - (location ?a))
      (sleeping-dragon - )
      (has ?h ?i - (holds ?h ?i))
      (visible ?a ?l - (perception ?a ?l))
      (hidden ?l - (not (visible agent ?l)))
      (reachable ?l1 ?l2 - and (at ?x ?l1) (moves-to ?x ?l2)))

     (:action go-to
       :parameters (?a ?l1 ?l2)
       :precondition (and (agent ?a) (reachable ?l1 ?l2))
       :effect (and (at ?a ?l2) (not (at ?a ?l1))))

     (:action take-sword
       :parameters (?h ?l)
       :precondition (and (agent hero) (at hero ?l) (hidden ?l))
       :effect (and (has hero sword) (not (hidden ?l))))

     (:action wake-dragon
       :parameters (?a)
       :precondition (and (agent ?a) (at ?a village))
       :effect (and (not (sleeping-dragon)) (visible dragon cave)))

     (:action fight-dragon
       :parameters (?h)
       :precondition (and (has ?h sword) (visible hero cave) (at ?h cave))
       :effect (and (defeated dragon) (not (exists dragon))))
   )