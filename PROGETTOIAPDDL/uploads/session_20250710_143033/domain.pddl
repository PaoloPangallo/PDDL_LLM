(define (domain cyber-heist-mission)
    (:requirements :strips :typing)
    (:types
    
        
        entity
        
        agent - entity
        
        object - entity
        
        location
        
    
    )
    (:predicates
    
        (at ?x - entity ?l - location)
    
        (connected ?from - location ?to - location)
    
        (hacked ?o - object)
    
        (has ?h - agent ?o - object)
    
        (delivered ?o - object)
    
    )
    
    (:action move
        :parameters (
        
        ?h - agent
        
        ?from - location
        
        ?to - location
        
        )
        :precondition (and
        
            
            (at ?h ?from)
            
        
            
            (connected ?from ?to)
            
        
        
        )
        :effect (and
        
            (at ?h ?to)
        
        
            (not (at ?h ?from))
        
        )
    )
    
    (:action hack-cctv
        :parameters (
        
        ?h - agent
        
        ?g - object
        
        ?l - location
        
        )
        :precondition (and
        
            
            (at ?h ?l)
            
        
            
            (at ?g ?l)
            
        
        
        )
        :effect (and
        
            (hacked ?g)
        
        
        )
    )
    
    (:action bribe-insider
        :parameters (
        
        ?h - agent
        
        ?i - agent
        
        ?c - object
        
        ?l - location
        
        )
        :precondition (and
        
            
            (at ?h ?l)
            
        
            
            (at ?i ?l)
            
        
            
            (at ?c ?l)
            
        
        
        )
        :effect (and
        
            (has ?h ?c)
        
        
            (not (at ?c ?l))
        
        )
    )
    
    (:action hack-mainframe
        :parameters (
        
        ?h - agent
        
        ?m - object
        
        ?l - location
        
        )
        :precondition (and
        
            
            (at ?h ?l)
            
        
            
            (at ?m ?l)
            
        
        
        )
        :effect (and
        
            (hacked ?m)
        
        
        )
    )
    
    (:action transfer-ai
        :parameters (
        
        ?h - agent
        
        ?o - object
        
        ?l - location
        
        )
        :precondition (and
        
            
            (at ?h ?l)
            
        
            
            (at ?o ?l)
            
        
        
        )
        :effect (and
        
            (has ?h ?o)
        
        
            (not (at ?o ?l))
        
        )
    )
    
    (:action escape-rooftop
        :parameters (
        
        ?h - agent
        
        ?from - location
        
        ?to - location
        
        )
        :precondition (and
        
            
            (at ?h ?from)
            
        
            
            (connected ?from ?to)
            
        
        
        )
        :effect (and
        
            (at ?h ?to)
        
        
            (not (at ?h ?from))
        
        )
    )
    
    (:action escape-metro
        :parameters (
        
        ?h - agent
        
        ?from - location
        
        ?to - location
        
        )
        :precondition (and
        
            
            (at ?h ?from)
            
        
            
            (connected ?from ?to)
            
        
        
        )
        :effect (and
        
            (at ?h ?to)
        
        
            (not (at ?h ?from))
        
        )
    )
    
    (:action deliver-ai
        :parameters (
        
        ?h - agent
        
        ?o - object
        
        ?l - location
        
        )
        :precondition (and
        
            
            (at ?h ?l)
            
        
            
            (has ?h ?o)
            
        
        
        )
        :effect (and
        
            (delivered ?o)
        
        
        )
    )
    
)