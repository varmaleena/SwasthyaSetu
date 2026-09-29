from alembic.config import Config
from alembic import command
from services.api.db import engines_from_env
def main():
    for state, engine in engines_from_env().items():
        config = Config('alembic.ini')
        config.attributes['url'] = engine.url.render_as_string(hide_password=False)
        command.upgrade(config, 'head')
        print(f'State {state}: migrated to head')
if __name__ == '__main__': main()
