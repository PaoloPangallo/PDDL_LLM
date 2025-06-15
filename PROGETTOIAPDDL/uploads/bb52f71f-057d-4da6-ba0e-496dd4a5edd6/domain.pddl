(define (domain la-spada-di-varnak)
  :requirements :strips
  :types agent location
  :predicates
    (at ?a ?l)   ; il tipo ?a è un'istanza di agent e ?l è un'istanza di location
    (has-sword ?a) ; se il tipo ?a ha la spada
    (asleep ?a)  ; se il tipo ?a dorme
    (in-cave ?l) ; se la location ?l è una caverna
    (sleeping-dragon ?l) ; se nella location ?l c'è un drago addormentato

  :action move-agent
    :parameters (?a ?from ?to)
    :precondition (and (at ?a ?from) (not (in-cave ?to)))
    :effect (and (not (at ?a ?from)) (at ?a ?to))

  :action take-sword
    :parameters (?a)
    :precondition (and (has-sword cave) (at hero cave))
    :effect (and (not (has-sword cave)) (has-sword ?a))

  :action wake-dragon
    :parameters (?a)
    :precondition (and (asleep dragon-cave) (at ?a dragon-cave))
    :effect (and (not (asleep dragon-cave)))

  :action fight-dragon
    :parameters (?a)
    :precondition (and (has-sword ?a) (at ?a dragon-cave) (asleep dragon-cave))
    :effect (and (not (sleeping-dragon dragon-cave)) (not (at ?a dragon-cave)))
)