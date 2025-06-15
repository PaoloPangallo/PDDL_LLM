(define (domain swords-and-dragons)
     (:requirements :equality :quantifiers :negative :action-cost)
     (:types agent location object action)
     (:predicates
      (at ?a - location) ; l'agente è in una determinata posizione
      (has ?a - object)   ; l'agente ha un oggetto
      (sleeping ?o - dragon) ; il drago dorme
      (hidden ?l - cave)  ; la caverna è nascosta
     )
     (:action wake-dragon
       :parameters (?d dragon)
       :precondition (and (at ?d location) (sleeping ?d))
       :effect (not (sleeping ?d)))

     (:action explore-cave
       :parameters (?l cave)
       :precondition (at ?h location)
       :effect (if (hidden ?l) (and (not (hidden ?l)) (at ?h ?l)) ; se la caverna è nascosta, rimuove il predicato hidden e aggiunge l'at
                    (at ?h location)))

     (:action take-sword
       :parameters (?c cave) (?s sword)
       :precondition (and (at ?h ?c) (hidden ?c))
       :effect (if (hidden ?c) (and (not (hidden ?c)) (has ?h ?s)) ; se la caverna è nascosta, rimuove il predicato hidden e aggiunge l'has
                    (at ?h location)))
     (:action fight-dragon
       :parameters (?d dragon)
       :precondition (and (has ?h sword) (at ?h location) (at ?d location))
       :effect (if (sleeping ?d) (and (not (sleeping ?d)) (defeated ?d)) ; se il drago dorme, lo sveglia e aggiunge defeated
                    (defeated ?d)))
   )