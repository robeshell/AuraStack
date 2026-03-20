# -*- coding: utf-8 -*-
"""看板页 service 层"""

from datetime import date

from backend.app.component_center.crud.kanban_page import KanbanPageCRUD
from backend.app.component_center.schema.kanban_page import (
    PRIORITY_VALUES,
    parse_bool,
    parse_int,
)


class KanbanPageServiceError(Exception):
    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}


class KanbanPageService:
    def __init__(self, db, board_model, card_model):
        self.db = db
        self.KanbanBoard = board_model
        self.KanbanCard = card_model
        self.crud = KanbanPageCRUD(db, board_model, card_model)

    # ── 看板列 ──────────────────────────────────────────────────────────

    def get_all_boards(self):
        boards = self.crud.all_boards()
        return [b.to_dict(include_cards=True) for b in boards]

    def create_board(self, data):
        title = str(data.get('title') or '').strip()
        board_code = str(data.get('board_code') or '').strip()
        if not title:
            raise KanbanPageServiceError('列标题不能为空')
        if not board_code:
            raise KanbanPageServiceError('列编码不能为空')
        if self.crud.get_board_by_code(board_code):
            raise KanbanPageServiceError('列编码已存在')

        board = self.KanbanBoard(
            title=title,
            board_code=board_code,
            color=str(data.get('color') or '#4080FF').strip() or '#4080FF',
            sort_order=parse_int(data.get('sort_order'), default=0),
            wip_limit=parse_int(data.get('wip_limit'), default=0),
            is_active=parse_bool(data.get('is_active'), default=True),
        )
        try:
            self.crud.add(board)
            self.crud.commit()
            return board.to_dict(include_cards=True), 201
        except Exception as e:
            self.crud.rollback()
            raise KanbanPageServiceError(str(e), 500) from e

    def update_board(self, board, data):
        if 'title' in data and not str(data.get('title') or '').strip():
            raise KanbanPageServiceError('列标题不能为空')

        field_map = {
            'title':      lambda v: str(v or '').strip(),
            'color':      lambda v: str(v or '#4080FF').strip() or '#4080FF',
            'sort_order': lambda v: parse_int(v, default=board.sort_order or 0),
            'wip_limit':  lambda v: parse_int(v, default=board.wip_limit or 0),
            'is_active':  lambda v: parse_bool(v, default=board.is_active),
        }
        for field, converter in field_map.items():
            if field in data:
                setattr(board, field, converter(data[field]))
        try:
            self.crud.commit()
            return board.to_dict(include_cards=True)
        except Exception as e:
            self.crud.rollback()
            raise KanbanPageServiceError(str(e), 500) from e

    def delete_board(self, board):
        try:
            self.crud.delete(board)
            self.crud.commit()
            return {'message': '删除成功'}
        except Exception as e:
            self.crud.rollback()
            raise KanbanPageServiceError(str(e), 500) from e

    # ── 卡片 ────────────────────────────────────────────────────────────

    def _parse_due_date(self, value):
        if not value:
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    def create_card(self, data):
        title = str(data.get('title') or '').strip()
        card_code = str(data.get('card_code') or '').strip()
        board_id = parse_int(data.get('board_id'), default=0)

        if not title:
            raise KanbanPageServiceError('卡片标题不能为空')
        if not card_code:
            raise KanbanPageServiceError('卡片编码不能为空')
        if not board_id or not self.crud.get_board_or_404(board_id):
            raise KanbanPageServiceError('所属列不存在')
        if self.crud.get_card_by_code(card_code):
            raise KanbanPageServiceError('卡片编码已存在')

        priority = str(data.get('priority') or 'medium').strip()
        if priority not in PRIORITY_VALUES:
            priority = 'medium'

        card = self.KanbanCard(
            board_id=board_id,
            title=title,
            card_code=card_code,
            description=str(data.get('description') or '').strip() or None,
            priority=priority,
            assignee=str(data.get('assignee') or '').strip() or None,
            due_date=self._parse_due_date(data.get('due_date')),
            tags=str(data.get('tags') or '').strip() or None,
            sort_order=parse_int(data.get('sort_order'), default=0),
            is_active=parse_bool(data.get('is_active'), default=True),
        )
        try:
            self.crud.add(card)
            self.crud.commit()
            return card.to_dict(), 201
        except Exception as e:
            self.crud.rollback()
            raise KanbanPageServiceError(str(e), 500) from e

    def update_card(self, card, data):
        if 'title' in data and not str(data.get('title') or '').strip():
            raise KanbanPageServiceError('卡片标题不能为空')

        if 'board_id' in data:
            board_id = parse_int(data['board_id'], default=0)
            if board_id:
                card.board_id = board_id

        field_map = {
            'title':       lambda v: str(v or '').strip(),
            'description': lambda v: str(v or '').strip() or None,
            'assignee':    lambda v: str(v or '').strip() or None,
            'tags':        lambda v: str(v or '').strip() or None,
            'sort_order':  lambda v: parse_int(v, default=card.sort_order or 0),
            'is_active':   lambda v: parse_bool(v, default=card.is_active),
        }
        for field, converter in field_map.items():
            if field in data:
                setattr(card, field, converter(data[field]))

        if 'priority' in data:
            p = str(data['priority'] or 'medium').strip()
            card.priority = p if p in PRIORITY_VALUES else 'medium'

        if 'due_date' in data:
            card.due_date = self._parse_due_date(data['due_date'])

        try:
            self.crud.commit()
            return card.to_dict()
        except Exception as e:
            self.crud.rollback()
            raise KanbanPageServiceError(str(e), 500) from e

    def delete_card(self, card):
        try:
            self.crud.delete(card)
            self.crud.commit()
            return {'message': '删除成功'}
        except Exception as e:
            self.crud.rollback()
            raise KanbanPageServiceError(str(e), 500) from e

    def reorder_cards(self, items):
        """批量更新卡片的 board_id 和 sort_order"""
        if not isinstance(items, list):
            raise KanbanPageServiceError('参数格式错误，需要数组')
        try:
            for item in items:
                card_id = parse_int(item.get('id'), default=0)
                board_id = parse_int(item.get('board_id'), default=0)
                sort_order = parse_int(item.get('sort_order'), default=0)
                if not card_id:
                    continue
                card = self.KanbanCard.query.get(card_id)
                if card:
                    if board_id:
                        card.board_id = board_id
                    card.sort_order = sort_order
            self.crud.commit()
            return {'message': '排序已保存'}
        except Exception as e:
            self.crud.rollback()
            raise KanbanPageServiceError(str(e), 500) from e
