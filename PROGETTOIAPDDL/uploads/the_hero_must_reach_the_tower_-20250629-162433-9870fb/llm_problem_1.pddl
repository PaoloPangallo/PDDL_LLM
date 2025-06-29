(define (problem <problem-name> :domain <domain-name>)
  (:object-schema (and (InstanceOf ?x1 <type1>) ...))
  (:init (and (predicate P1 ?x1) ...)) ;; replace `P1` with the actual predicate name
  (:goal (and (not (predicate P1 ?x1)) ...))) ;; replace `P1` with the actual predicate name