(define (domain swords-and-dragons)
     (:requirements :equality :prehensile-object :static)
     (:types agent location dragon sword)
     (:predicates
      (at ?x ?y)               ; l'agente si trova in una determinata località
      (held ?x ?y)             ; l'oggetto è posseduto dall'agente
      (sleeping-dragon ?d)     ; il drago dorme nella località d
      (hidden-sword ?l)        ; la spada è nascosta nella località l
      (has ?a ?s)              ; l'agente ha la spada
      (defeated ?d)            ; l'agente ha sconfitto il drago
     )
     (:action wake-dragon
       :parameters (?d)
       :precondition (sleeping-dragon ?d)
       :effect (not (sleeping-dragon ?d))
     )
     (:action find-sword
       :parameters (?l)
       :precondition (and (at hero ?l) (hidden-sword ?l))
       :effect (and (not (hidden-sword ?l)) (held sword hero)))
     (:action wield-sword
       :parameters (?a ?s)
       :precondition (and (held ?s hero))
       :effect (has ?a ?s)
     )
     (:action defeat-dragon
       :parameters (?d)
       :precondition (and (at hero (location ?d)) (has sword hero))
       :effect (and (defeated ?d) (not (sleeping-dragon ?d)))
     )
   )