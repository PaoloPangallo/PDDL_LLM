(define la-spada-di-varnak
     (:requirements ignore
       :types agent location action success state
       :predicates (at agent location)
                (has agent object)
                (sleeping dragon)
                (defeated dragon)
                (sword-in cave)
                (sword-in hand))
     (:action move
       :parameters (?a ?b)
       :precondition (and (at ?a ?b) (not (= ?a ?b)))
       :effect (and (at ?a ?b) (not (at ?b ?a))))
     (:action pick-up
       :parameters (?a ?o)
       :precondition (and (at ?a location) (sword-in ?o))
       :effect (and (has ?a ?o) (not (sword-in ?o))))
     (:action drop
       :parameters (?a ?o)
       :precondition (and (has ?a ?o))
       :effect (and (not (has ?a ?o)) (sword-in ?o)))
     (:action fight
       :parameters (?h ?d)
       :precondition (and (has ?h sword) (sleeping ?d))
       :effect (if (= ?r success) (defeated ?d)
                   (and (not (defeated ?d)) (sleeping ?d))))
     (:action wake-dragon
       :parameters (?d)
       :precondition (and (at hero cave) (sword-in hand))
       :effect (if (= ?r success) (not (sleeping ?d))
                   (and (sleeping ?d))))
   )