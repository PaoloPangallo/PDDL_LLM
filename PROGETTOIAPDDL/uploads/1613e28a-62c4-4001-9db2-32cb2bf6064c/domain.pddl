(define (domain la-spada-di-varnak)
     :requirements :strips
     :types agent location object
     :predicates
       (at ?x - location)
       (hidden ?o - location)
       (sleeping ?m - monster)
       (has ?a - object)
       (defeated ?m - monster)
     :actions
       (move
         :parameters (?a - agent) (?l1 - location) (?l2 - location)
         :precondition (and (at ?a ?l1) (distinct ?a ?l2))
         :effect (and (not (at ?a ?l1)) (at ?a ?l2)))
       (search
         :parameters (?a - agent) (?o - object)
         :precondition (and (at ?a village) (hidden ?o))
         :effect (if (= (find-distance ?o cave) 1)
                   (and (not (hidden ?o)) (at ?a cave))
                   (fail)))
       (slay
         :parameters (?h - hero) (?m - monster)
         :precondition (and (has ?h sword) (sleeping ?m))
         :effect (and (not (sleeping ?m)) (defeated ?m)))
   )