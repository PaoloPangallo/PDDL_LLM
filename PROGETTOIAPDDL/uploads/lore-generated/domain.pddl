; Domain per la storia di "La Spada di Varnak"
 (define (domain varnak)
   (:requirements :equality-comparison :function :math :quantifiers)
   (:action-predicates (and take- item-held pickup drop) (and in- cave sleep-dragon fight-dragon has-sword) )
   ; Tipi di oggetti e agenti
   (:types hero monster sword cave)
   (:constants ?hero ?monster1 ?monster2 ?sword ?cave)
   ; Predicati
   (:predicate (item-held ?x ?y)
     "Il ?x è in mano al ?y" )
   (:predicate (in- ?x ?y)
     "?x si trova in ?y" )
   (:predicate (sleep-dragon ?x)
     "Il drago dorme" )
   (:predicate (fight-dragon ?x)
     "Il ?x combatte contro il drago" )
   (:predicate (has-sword ?x)
     "Il ?x possiede la spada" )
   ; Azione di prendere un oggetto
   (:action take
     :parameters (?x)
     :precondition (and (in- ?x ?cave) (not (item-held ?hero ?x)))
     :effect (and (not (in- ?x ?cave)) (item-held ?hero ?x)) )
   ; Azione di prelevare la spada dalla grotta
   (:action pickup-sword
     :parameters ()
     :precondition (and (in- ?sword ?cave) (not (has-sword ?hero)))
     :effect (and (item-held ?hero ?sword) (not (in- ?sword ?cave)) (has-sword ?hero)) )
   ; Azione di mettere a terra un oggetto
   (:action drop
     :parameters (?x)
     :precondition (and (item-held ?y ?x))
     :effect (and (not (item-held ?y ?x)) (in- ?x cave)))
   ; Azione di andare nella grotta
   (:action enter-cave
     :parameters ()
     :precondition (not (in- ?hero ?cave))
     :effect (in- ?hero ?cave) )
   ; Azione di uscire dalla grotta
   (:action exit-cave
     :parameters ()
     :precondition (in- ?hero ?cave)
     :effect (not (in- ?hero ?cave)) )
   ; Azione di dormire o svegliarsi il drago
   (:action sleep
     :parameters ()
     :precondition (in- ?monster1 ?cave)
     :effect (sleep-dragon ?monster1) )
   ; Azione di svegliare il drago
   (:action wake-up
     :parameters ()
     :precondition (and (sleep-dragon ?monster1) (not (fight-dragon ?hero)))
     :effect (not (sleep-dragon ?monster1)) )
   ; Azione di combatte contro il drago
   (:action fight
     :parameters ()
     :precondition (and (in- ?monster1 ?cave) (has-sword ?hero))
     :effect (fight-dragon ?hero) )
   ; Azione di sconfiggere il drago
   (:action defeat-dragon
     :parameters ()
     :precondition (and (fight-dragon ?hero) (has-sword ?hero))
     :effect (not (sleep-dragon ?monster1) (not (in- ?monster1 cave))) )
   ; Azione di porre fine all'azione corrente
   (:action do-nothing
     :parameters ()
     :precondition true
     :effect nil)
 )