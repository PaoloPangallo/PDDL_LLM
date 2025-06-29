(define (problem problem-name :domain domain-name)
  (:object-schemas (ObjectSchema1 ObjectSchema2 ...))
  (:init
    (P1 ?o - ObjectSchema1)     ; Initialize the state here
    (not P2 ?o ?o)               ; Ensure that there are no initial conflicts
    ...
  )
  (:goal (P4 ?o))                 ; Define the goal here
  (:action-schemas (ActionScheme1 ActionScheme2 ...))
)