(define (domain swords-and-dragons)
     :requirements :strips
     :types agent location
     :predicates
       (at ?a ?l)
       (has ?a ?o)
       (alive ?d)
       (sleeping ?d)
       (in-cave ?c)
       (hidden ?c)
     :action take-sword
       :parameters (?a) (?s)
       :precondition (and (at ?a cave) (hidden cave))
       :effect (and (has ?a sword) (not (hidden cave)))
     :action wake-dragon
       :parameters (?d)
       :precondition (and (at ?d cave) (sleeping ?d))
       :effect (not (sleeping ?d))
     :action fight-dragon
       :parameters (?a) (?d)
       :precondition (and (at ?a cave) (alive ?d) (has ?a sword))
       :effect (and (defeated ?d) (not (alive ?d)))
     :action leave-cave
       :parameters (?a)
       :precondition (and (at ?a cave) (not (hidden cave)))
       :effect (not (at ?a cave)))