(define (domain scarc_domain)
  (:requirements :strips :typing)

  (:types
    location
    object
    agent - object
    npc - object
    security_system - object
    credential - object
    device - object
    artifact - object
    studente_type - agent
    assistente_type - npc
    sistema_sicurezza_type - security_system
    codice_quantum_type - credential
  )

  (:predicates
    (at ?x - object ?y - location)
    (connected ?x - location ?y - location)
    (has ?x - agent ?o - object)
    (disabled ?x - security_system)
    (convinced ?x - npc)
    (delivered ?x - object)
  )

  (:action move
    :parameters (?a - agent ?from - location ?to - location)
    :precondition (and (at ?a ?from) (connected ?from ?to))
    :effect (and (not (at ?a ?from)) (at ?a ?to))
  )

  (:action disattiva_sistema
    :parameters (?a - agent ?s - security_system ?l - location)
    :precondition (and (at ?a ?l) (at ?s ?l))
    :effect (disabled ?s)
  )

  (:action convinci_assistente
    :parameters (?a - agent ?as - npc ?l - location)
    :precondition (and (at ?a ?l) (at ?as ?l))
    :effect (convinced ?as)
  )

  (:action prendi_codice
    :parameters (?a - agent ?c - credential ?l - location ?s - security_system ?as - npc)
    :precondition (and
      (at ?a ?l)
      (at ?c ?l)
      (or (disabled ?s) (convinced ?as))
    )
    :effect (and (not (at ?c ?l)) (has ?a ?c))
  )

  (:action fuggi
    :parameters (?a - agent ?from - location ?to - location)
    :precondition (and (at ?a ?from) (connected ?from ?to))
    :effect (and (not (at ?a ?from)) (at ?a ?to))
  )

  (:action consegna_codice
    :parameters (?a - agent ?c - credential ?l - location)
    :precondition (and (at ?a ?l) (has ?a ?c))
    :effect (delivered ?c)
  )
)
