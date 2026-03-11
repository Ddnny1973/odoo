CREATE or replace FUNCTION gestor_tg_desactiva_usuario() RETURNS TRIGGER AS $$
BEGIN

	if new.active=false then
		update res_users set active=false
		where id=new.user_id;
	end if;

	if new.active=true then
		update res_users set active=true
		where id=new.user_id;
	end if;

	RETURN NULL;

END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS gestor_tg_desactiva_usuario ON hr_employee;
CREATE TRIGGER gestor_tg_desactiva_usuario after update ON hr_employee FOR EACH ROW EXECUTE PROCEDURE gestor_tg_desactiva_usuario();
