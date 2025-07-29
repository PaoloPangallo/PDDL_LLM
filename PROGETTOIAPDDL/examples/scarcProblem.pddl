(define (problem scarc_problem)
  (:domain scarc_domain)

  (:objects
    studente - studente_type
    assistente - assistente_type
    sistema_sicurezza - sistema_sicurezza_type
    codice_quantum - codice_quantum_type
    mainframe - device
    ScrittoIA - artifact
    lab_longo aula_reti bar_TAU smartlab tetto_cubo44 tunnel_dimes - location
  )

  (:init
    (at studente lab_longo)
    (at sistema_sicurezza aula_reti)
    (at assistente bar_TAU)
    (at codice_quantum smartlab)
    (connected lab_longo aula_reti)
    (connected lab_longo bar_TAU)
    (connected aula_reti smartlab)
    (connected smartlab aula_reti)
    (connected bar_TAU smartlab)
    (connected smartlab bar_TAU)
    (connected smartlab tetto_cubo44)
    (connected tetto_cubo44 smartlab)
    (connected smartlab tunnel_dimes)
    (connected tunnel_dimes smartlab)
    (connected tunnel_dimes lab_longo)
    (connected tetto_cubo44 lab_longo)
  )

  (:goal
    (and
      (at studente lab_longo)
      (delivered codice_quantum)
    )
  )
)
