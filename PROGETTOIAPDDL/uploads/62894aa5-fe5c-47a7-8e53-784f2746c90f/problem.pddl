(define (problem swords-and-dragons)
     (:objects (?h hero) (?d dragon) (?c cave) (?s sword))
     (:init (at ?h village) (hidden sword cave) (sleeping dragon))
     (:goal (and (has ?h sword) (defeated dragon))) ; l'obiettivo è di aver la spada e aver sconfitto il drago
   )