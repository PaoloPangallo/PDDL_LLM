(define (domain varnak)
  :requirements :strips
  :types agent location action
  :predicates
    (at ?a ?l) ; agente in posizione
    (has-sword ?a) ; agente ha la spada
    (dragon-asleep ?d) ; dragone addormentato
    (defeated ?d) ; dragone sconfitto
  :actions
    (move (:parameters ?a ?l1 ?l2)
      :precondition (and (at ?a ?l1) (location? ?l2))
      :effect (and (not (at ?a ?l1)) (at ?a ?l2)))
    (take-sword (:parameters ?a)
      :precondition (and (at ?a cave) (hidden sword cave))
      :effect (and (not (hidden sword cave)) (has-sword ?a)))
    (wake-dragon (:parameters ?a)
      :precondition (and (at ?a cave) (sleeping dragon))
      :effect (and (not (sleeping dragon)) (not (defeated ?a))))
    (fight (:parameters ?a ?d)
      :precondition (and (has-sword ?a) (at ?a ?d))
      :effect (and (defeated ?d)))
)