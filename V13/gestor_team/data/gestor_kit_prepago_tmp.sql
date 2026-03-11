-- Table: public.gestor_kit_prepago_tmp

-- DROP TABLE public.gestor_kit_prepago_tmp;

CREATE TABLE public.gestor_kit_prepago_tmp
(
    identificacion character(250) COLLATE pg_catalog."default",
    vendedor character(250) COLLATE pg_catalog."default",
    producto character(250) COLLATE pg_catalog."default",
    numerodefactura character(250) COLLATE pg_catalog."default",
    fechadeventa date,
    tipodeproducto character(250) COLLATE pg_catalog."default",
    cantidad character(250) COLLATE pg_catalog."default"
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.gestor_kit_prepago_tmp
    OWNER to odoo;
