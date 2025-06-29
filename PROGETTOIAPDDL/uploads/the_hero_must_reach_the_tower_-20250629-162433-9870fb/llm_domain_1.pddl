(define (domain <domain-name>))

;; Define types, functions, and initial state here...

(define (predicate <predicate-name> :schema (= ?x1 ?type) :filter (and (not (equal ?x1 nil)) (instance-of ?x1 ?type))) :role-schema (?x1))
;; ... where you need to replace `<domain-name>`, `<predicate-name>` and `<type>` with appropriate values