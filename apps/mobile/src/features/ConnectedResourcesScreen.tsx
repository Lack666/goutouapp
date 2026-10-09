import { useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import { BodyText, PrimaryButton, SectionCard, AppHeader, ScreenContainer } from '../components/ui';
import {
  ResourceInput,
  DevelopmentSessionControls,
} from '../components/DevelopmentSessionControls';
import { useResourceView, useSessionView, type Connection } from '../session/ConnectionProvider';
import type { ResourceKind, ResourceView } from '../contracts/resources';
import { useLocalNavigation, useRelationshipScope } from '../navigation/scope';

function ResourceList({
  kind,
  view,
  connection,
}: {
  kind: ResourceKind;
  view: ResourceView;
  connection: Connection;
}) {
  const page = view.pages[kind];
  const detail = view.details[kind];
  return (
    <SectionCard title={`${kind} · 服务器资源`}>
      <PrimaryButton
        label={`刷新 ${kind}`}
        disabled={page.status === 'loading'}
        variant="quiet"
        onPress={() => {
          void connection.resources.load(kind);
        }}
      />
      {page.status === 'loading' && <BodyText live>正在读取服务器…</BodyText>}
      {page.status === 'ready' && !page.items.length && <BodyText>当前用户没有 {kind}</BodyText>}
      {page.error && (
        <>
          <BodyText live>{page.error}</BodyText>
          <PrimaryButton
            label={`重试读取 ${kind}`}
            onPress={() => {
              void connection.resources.load(kind, page.cursor !== null);
            }}
          />
        </>
      )}
      {page.items.map((item) => (
        <PrimaryButton
          key={item.id}
          label={`查看 ${kind} ${'nickname' in item ? (item.nickname ?? '未提供名称') : 'displayName' in item ? item.displayName : item.id}`}
          variant="quiet"
          onPress={() => {
            void connection.resources.select(kind, item.id);
          }}
        />
      ))}
      <PrimaryButton
        label={`加载更多 ${kind}`}
        disabled={!page.cursor || page.status === 'loading'}
        variant="quiet"
        onPress={() => {
          void connection.resources.load(kind, true);
        }}
      />
      {detail.status === 'loading' && <BodyText>正在读取详情…</BodyText>}
      {detail.error && <BodyText live>{detail.error}</BodyText>}
      {detail.value && (
        <SectionCard title={`${kind} 详情`}>
          <BodyText>UUID：{detail.value.id}</BodyText>
          <BodyText>创建：{detail.value.createdAt}</BodyText>
          {'nickname' in detail.value && (
            <BodyText>名称：{detail.value.nickname ?? '未提供'}</BodyText>
          )}
          {'person' in detail.value && (
            <>
              <BodyText>
                所属 Person：{detail.value.person.nickname ?? '未提供'} · {detail.value.person.id}
              </BodyText>
              <BodyText>关系类型：{detail.value.label}</BodyText>
              <BodyText>状态：{detail.value.statusLabel}</BodyText>
              <BodyText>未提供互动、历史摘要或分析结果。</BodyText>
            </>
          )}
          {'relationshipId' in detail.value && (
            <BodyText>绑定关系：{detail.value.relationshipId ?? '无 · 通用会话'}</BodyText>
          )}
        </SectionCard>
      )}
    </SectionCard>
  );
}
function CreationState({
  kind,
  view,
  connection,
}: {
  kind: ResourceKind;
  view: ResourceView;
  connection: Connection;
}) {
  const create = view.creates[kind];
  return (
    <>
      {create.status === 'pending' && <BodyText live>正在提交创建…</BodyText>}
      {create.status === 'saved' && <BodyText live>服务器已确认保存 {kind}</BodyText>}
      {create.error && (
        <>
          <BodyText live>{create.error}</BodyText>
          <PrimaryButton
            label={`重试原创建 ${kind}`}
            onPress={() => {
              void connection.resources.retryCreate(kind);
            }}
          />
          <BodyText muted>
            重试保留首次请求的字段与 UUID。修改字段后请显式创建新资源；原请求可能已提交。
          </BodyText>
        </>
      )}
    </>
  );
}
export function ConnectedResourcesScreen({ connection }: { connection: Connection }) {
  const session = useSessionView(connection);
  const view = useResourceView(connection);
  const { back } = useLocalNavigation();
  const router = useRouter();
  const scope = useRelationshipScope();
  const [name, setName] = useState('');
  const [personId, setPersonId] = useState<string | null>(null);
  const [type, setType] = useState('');
  const [status, setStatus] = useState('');
  const [binding, setBinding] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    if (session.status === 'authenticated') {
      void connection.resources.load('persons');
      void connection.resources.load('relationships');
      void connection.resources.load('conversations');
    }
  }, [connection, session.status]);
  useEffect(() => {
    if (scope && session.status === 'authenticated')
      void connection.resources.select('relationships', scope);
  }, [connection, scope, session.status]);
  return (
    <ScreenContainer>
      <AppHeader
        title="关系资料"
        subtitle="Connected Development Mode · 当前会话的服务器资料"
        onBack={back}
      />
      <DevelopmentSessionControls />
      {session.status === 'authenticated' && (
        <>
          <ResourceList kind="persons" view={view} connection={connection} />
          <SectionCard title="创建 Person">
            <ResourceInput label="Person 显示名称" value={name} onChange={setName} />
            <PrimaryButton
              label="创建新 Person"
              disabled={!name.trim() || view.creates.persons.status === 'pending'}
              onPress={() => {
                if (connection.resources.reservePerson(name))
                  void connection.resources.retryCreate('persons');
              }}
            />
            <CreationState kind="persons" view={view} connection={connection} />
          </SectionCard>
          <ResourceList kind="relationships" view={view} connection={connection} />
          <SectionCard title="创建 Relationship">
            <BodyText>请显式选择对象并填写关系类型与状态；未知可填写 unknown。</BodyText>
            {view.pages.persons.items.map((person) => (
              <PrimaryButton
                key={person.id}
                label={`使用 Person ${person.nickname ?? '未提供'}`}
                selected={personId === person.id}
                variant="quiet"
                onPress={() => setPersonId(person.id)}
              />
            ))}
            <ResourceInput
              label="关系类型（必填）"
              value={type}
              onChange={setType}
              maxLength={40}
            />
            <ResourceInput
              label="关系状态（必填）"
              value={status}
              onChange={setStatus}
              maxLength={40}
            />
            <PrimaryButton
              label="创建新 Relationship"
              disabled={
                !personId ||
                !type.trim() ||
                !status.trim() ||
                view.creates.relationships.status === 'pending'
              }
              onPress={() => {
                if (personId && connection.resources.reserveRelationship(personId, type, status))
                  void connection.resources.retryCreate('relationships');
              }}
            />
            <CreationState kind="relationships" view={view} connection={connection} />
          </SectionCard>
          <ResourceList kind="conversations" view={view} connection={connection} />
          <SectionCard title="创建 Conversation">
            <BodyText>请选择通用会话或一个当前用户的关系。</BodyText>
            <PrimaryButton
              label="选择通用会话（无关系绑定）"
              variant="quiet"
              selected={binding === null}
              onPress={() => setBinding(null)}
            />
            {view.pages.relationships.items.map((relationship) => (
              <PrimaryButton
                key={relationship.id}
                label={`绑定 Relationship ${relationship.id}`}
                selected={binding === relationship.id}
                variant="quiet"
                onPress={() => setBinding(relationship.id)}
              />
            ))}
            <PrimaryButton
              label="创建新 Conversation"
              disabled={binding === undefined || view.creates.conversations.status === 'pending'}
              onPress={() => {
                if (binding !== undefined && connection.resources.reserveConversation(binding))
                  void connection.resources.retryCreate('conversations');
              }}
            />
            <CreationState kind="conversations" view={view} connection={connection} />
          </SectionCard>
          {view.selectedRelationshipId && (
            <SectionCard title="使用已选择的关系">
              {(['/chat', '/import', '/history'] as const).map((path) => (
                <PrimaryButton
                  key={path}
                  label={`前往${path === '/chat' ? '对话' : path === '/import' ? '导入' : '历史'}（尚未接入）`}
                  onPress={() =>
                    router.push({
                      pathname: path,
                      params: {
                        relationshipId: view.selectedRelationshipId!,
                        ...(view.selectedConversationId &&
                        view.details.conversations.value?.relationshipId ===
                          view.selectedRelationshipId
                          ? { conversationId: view.selectedConversationId }
                          : {}),
                      },
                    })
                  }
                />
              ))}
            </SectionCard>
          )}
        </>
      )}
    </ScreenContainer>
  );
}
